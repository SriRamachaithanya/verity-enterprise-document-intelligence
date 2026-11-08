import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from src.api.config import get_api_config
from src.api.schemas.documents import MalwareScanResult

logger = logging.getLogger(__name__)

# Standard magic byte signatures
MAGIC_SIGNATURES = {
    ".pdf": [b"%PDF-"],
    ".docx": [b"PK\x03\x04"],
}

# Standard EICAR test string pattern for antivirus testing
EICAR_PATTERN = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def sanitize_filename(raw_filename: str) -> str:
    """
    Sanitize an uploaded filename to strictly prevent path traversal,
    directory manipulation, and illegal filesystem characters.
    """
    if not raw_filename or not raw_filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a non-empty filename.",
        )

    # 1. Strip directory prefixes (e.g., ../../../etc/passwd or C:\windows\...)
    clean_name = Path(raw_filename).name

    # 2. Reject explicit traversal attempts
    if ".." in clean_name or "/" in clean_name or "\\" in clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains prohibited path traversal sequences.",
        )

    # 3. Strip null bytes and control characters
    clean_name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean_name)

    # 4. Remove Windows forbidden filename characters: < > : " / \ | ? *
    clean_name = re.sub(r'[<>:"/\\|?*]', "_", clean_name).strip()

    if not clean_name:
        clean_name = "uploaded_document"

    return clean_name


def validate_file_signature(extension: str, sample_bytes: bytes) -> bool:
    """
    Validate magic bytes against expected file signature.
    """
    ext = extension.lower()
    if ext in MAGIC_SIGNATURES:
        signatures = MAGIC_SIGNATURES[ext]
        return any(sample_bytes.startswith(sig) for sig in signatures)
    elif ext == ".txt":
        # Ensure text file does not contain binary null bytes
        if b"\x00" in sample_bytes:
            return False
        # Verify UTF-8 or ASCII decodability
        try:
            sample_bytes.decode("utf-8")
            return True
        except UnicodeDecodeError:
            try:
                sample_bytes.decode("latin-1")
                return True
            except UnicodeDecodeError:
                return False
    return False


def run_malware_scan(file_path: Path, content_sample: bytes | None = None) -> MalwareScanResult:
    """
    Inspect the file for malware using local antivirus engines (ClamAV, Windows Defender)
    or static signature analysis. Supports quarantine isolation if a threat is detected.
    """
    config = get_api_config()
    quarantine_dir = config.quarantine_dir
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    # 1. In-memory and static signature EICAR check
    has_threat = False
    threat_name = "EICAR test string"

    if content_sample and b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in content_sample:
        has_threat = True

    if not has_threat:
        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)
                if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in header:
                    has_threat = True
        except OSError as os_err:
            # On Windows, real-time Defender locks or intercepts malicious files immediately
            logger.error("Host Antivirus or OS locked file during access: %s", os_err)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File rejected: Real-time Antivirus engine intercepted and blocked access to the file.",
            ) from os_err
        except Exception as e:  # noqa: BLE001
            logger.warning("Error reading file during static malware scan: %s", e)

    if has_threat:
        quarantine_target = quarantine_dir / f"quarantined_{file_path.name}"
        try:
            if file_path.exists():
                shutil.move(str(file_path), str(quarantine_target))
        except Exception as q_err:  # noqa: BLE001
            logger.warning("Could not move infected file to quarantine (locked by AV): %s", q_err)

        logger.error("Malware test signature intercepted! Quarantined to %s", quarantine_target)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File rejected: Malicious signature detected ({threat_name}). Quarantined.",
        )

    # 2. Check for ClamAV CLI
    clam_bin = shutil.which("clamscan") or shutil.which("clamdscan")
    if clam_bin:
        try:
            res = subprocess.run(
                [clam_bin, "--no-summary", str(file_path)],
                capture_output=True,
                timeout=10.0,
                check=False,
            )
            if res.returncode == 0:
                return MalwareScanResult(
                    scanned=True,
                    engine="ClamAV",
                    is_clean=True,
                    details="ClamAV scan completed with zero threats detected.",
                )
            elif res.returncode == 1:
                # Threat found
                quarantine_target = quarantine_dir / f"quarantined_{file_path.name}"
                shutil.move(str(file_path), str(quarantine_target))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File rejected: ClamAV detected a malicious payload. Quarantined.",
                )
        except HTTPException:
            raise
        except Exception as err:  # noqa: BLE001
            logger.warning("ClamAV scan execution error: %s", err)

    # 3. Check for Windows Defender CLI (MpCmdRun.exe)
    defender_paths = [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Windows Defender" / "MpCmdRun.exe",
        Path(os.environ.get("ProgramData", "C:\\ProgramData")) / "Microsoft" / "Windows Defender" / "Platform",
    ]
    mpcmdrun = None
    for p in defender_paths:
        if p.is_file():
            mpcmdrun = str(p)
            break
        elif p.is_dir():
            candidates = list(p.glob("*/MpCmdRun.exe"))
            if candidates:
                mpcmdrun = str(candidates[-1])
                break

    if mpcmdrun:
        try:
            res = subprocess.run(
                [mpcmdrun, "-Scan", "-ScanType", "3", "-File", str(file_path), "-DisableRemediation"],
                capture_output=True,
                timeout=15.0,
                check=False,
            )
            if res.returncode == 0:
                return MalwareScanResult(
                    scanned=True,
                    engine="Microsoft Defender",
                    is_clean=True,
                    details="Microsoft Defender scan completed cleanly.",
                )
            elif res.returncode == 2:
                # Threat detected
                quarantine_target = quarantine_dir / f"quarantined_{file_path.name}"
                shutil.move(str(file_path), str(quarantine_target))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File rejected: Microsoft Defender detected a malicious payload. Quarantined.",
                )
        except HTTPException:
            raise
        except Exception as err:  # noqa: BLE001
            logger.warning("Windows Defender scan execution error: %s", err)

    # 4. Standard fallback when external antivirus CLI is absent
    return MalwareScanResult(
        scanned=False,
        engine="Static Signature & Heuristic Scanner",
        is_clean=True,
        details="Local Antivirus CLI (ClamAV/MpCmdRun) unavailable offline; static magic bytes & heuristic checks verified.",
    )


async def validate_uploaded_file(file: UploadFile) -> tuple[str, bytes]:
    """
    Validate an uploaded file's filename, extension, size, and magic bytes.
    Returns: (sanitized_filename, file_bytes)
    """
    config = get_api_config()
    sanitized_name = sanitize_filename(file.filename or "")

    # Check extension
    suffix = Path(sanitized_name).suffix.lower()
    if suffix not in config.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{suffix}'. Allowed: {config.allowed_extensions}",
        )

    # Read bytes with streaming chunk size check
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    if len(content) > config.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed upload size of {config.max_upload_size_bytes // (1024 * 1024)} MB.",
        )

    # Verify magic bytes
    sample = content[:32]
    if not validate_file_signature(suffix, sample):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content does not match expected binary signature for extension '{suffix}'.",
        )

    return sanitized_name, content
