#!/usr/bin/env python3

from __future__ import annotations
import logging
from pathlib import Path


def setup_logger(name: str, log_file: str | None = None,
                  level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # tránh add handler trùng lặp nếu hàm này bị gọi nhiều lần
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


if __name__ == "__main__":
    log = setup_logger("recon", log_file="results/recon.log", level=logging.DEBUG)

    log.debug("Chi tiết kỹ thuật - chỉ hiện khi level=DEBUG")
    log.info("subfinder tìm được 42 subdomain")
    log.warning("dnsx: 3 subdomain không resolve được")

    try:
        1 / 0
    except ZeroDivisionError:
        # exc_info=True: log kèm traceback đầy đủ, hữu ích khi tool
        # chạy nền/không có người ngồi xem trực tiếp lúc lỗi xảy ra
        log.error("Lỗi khi xử lý kết quả", exc_info=True)

    print("\n--- Thử đổi sang level=WARNING, DEBUG/INFO sẽ biến mất ---")
    log2 = setup_logger("recon_warn_only", level=logging.WARNING)
    log2.debug("Dòng này sẽ KHÔNG hiện")
    log2.info("Dòng này cũng KHÔNG hiện")
    log2.warning("Chỉ dòng WARNING/ERROR mới hiện")

    print(f"\n(Đã ghi thêm vào file: results/recon.log)")

    # Áp dụng thực tế: mỗi module (subprocess wrapper, http client...)
    # tự lấy logger riêng bằng logging.getLogger(__name__), dùng
    # chung cấu hình đã setup ở logger gốc "recon".

    # TODO tự thử: mở file results/recon.log sau khi chạy xong, xem
    # traceback của lỗi ZeroDivisionError được ghi đầy đủ thế nào.
