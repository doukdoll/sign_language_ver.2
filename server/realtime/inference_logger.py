import os
import time
from typing import List, Dict, Any, Optional

import numpy as np
from utils.logger import get_logger

logger = get_logger("kslt.inference_logger")


class InferenceLogger:
    """
    실시간 추론에서 새 토큰(단어)이 방출될 때 사용된 특징 윈도우를 누적 저장하고,
    프로그램 종료 시 CSV 파일들로 저장하는 로거.
    (NumPy .npz 파일 저장은 제거됨 - 저장 공간 절약 및 바이너리 파일 방지)
    """

    def __init__(
        self,
        win: int,
        save_dir: str = "data",
        prefix: str = "inference_keypoints",
        save_csv_summary: bool = True,
        save_windows_csv: bool = True,  # 기본적으로 CSV 저장 활성화
        save_keypoints_csv: bool = True,  # 키포인트 데이터를 CSV로 저장
    ) -> None:
        self.win = win
        self.save_dir = save_dir
        self.prefix = prefix
        os.makedirs(self.save_dir, exist_ok=True)
        self._entries: List[Dict[str, Any]] = []
        self.save_csv_summary = save_csv_summary
        self.save_windows_csv = save_windows_csv
        self.save_keypoints_csv = save_keypoints_csv

    def add(self, label_id: int, word: str, feat_window: Optional[np.ndarray]) -> None:
        if feat_window is None:
            return
        try:
            window = np.array(feat_window, dtype=np.float32, copy=True)
        except Exception:
            return
        self._entries.append({
            "timestamp": float(time.time()),
            "label_id": int(label_id),
            "word": str(word),
            "window": window,
        })

    def save(self) -> None:
        if not self._entries:
            logger.info("저장할 추론 로그가 없습니다.")
            return
        ts = time.strftime("%Y%m%d_%H%M%S")

        # NumPy .npz 파일 저장은 제거 (저장 공간 절약 및 불필요한 바이너리 파일 방지)
        # out_path = os.path.join(self.save_dir, f"{self.prefix}_{ts}.npz")
        # try:
        #     windows = np.stack([e["window"] for e in self._entries], axis=0)
        #     label_ids = np.array([e["label_id"] for e in self._entries], dtype=np.int32)
        #     words = np.array([e["word"] for e in self._entries], dtype=object)
        #     timestamps = np.array([e["timestamp"] for e in self._entries], dtype=np.float64)
        #     np.savez_compressed(
        #         out_path,
        #         windows=windows,
        #         label_ids=label_ids,
        #         words=words,
        #         timestamps=timestamps,
        #         win=np.array(self.win, dtype=np.int32),
        #     )
        #     logger.info(f"추론 키포인트 로그 저장: {out_path}")
        # except Exception as e:
        #     logger.error(f"NumPy 로그 저장 실패: {e}")

        # CSV 저장은 유지
        try:
            windows = np.stack([e["window"] for e in self._entries], axis=0)

            if self.save_csv_summary:
                import csv
                csv_path = os.path.join(self.save_dir, f"{self.prefix}_{ts}_summary.csv")
                with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["index", "timestamp", "datetime", "label_id", "word", "win", "feat_dim"])
                    for i, e in enumerate(self._entries):
                        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e["timestamp"]))
                        writer.writerow([i, f"{e['timestamp']:.6f}", dt, e["label_id"], e["word"], self.win, e["window"].shape[1]])
                logger.info(f"요약 CSV 저장: {csv_path}")

            if self.save_windows_csv:
                dir_path = os.path.join(self.save_dir, f"{self.prefix}_{ts}_windows")
                os.makedirs(dir_path, exist_ok=True)
                for i, e in enumerate(self._entries):
                    safe_word = str(e["word"]).replace(os.sep, "_")
                    file_name = f"entry_{i:03d}_{safe_word}_{e['label_id']}.csv"
                    file_path = os.path.join(dir_path, file_name)
                    try:
                        np.savetxt(file_path, e["window"], delimiter=",", fmt="%.6f")
                    except Exception:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write("저장 실패")
                logger.info(f"윈도우 CSV 디렉터리 저장: {dir_path}")

            if self.save_keypoints_csv:
                keypoints_csv_path = os.path.join(self.save_dir, f"{self.prefix}_{ts}_keypoints.csv")
                try:
                    with open(keypoints_csv_path, "w", encoding="utf-8") as f:
                        # 헤더 작성
                        header = ["index", "timestamp", "datetime", "label_id", "word"]
                        # 키포인트 특징 차원만큼 컬럼 추가 (274차원)
                        for i in range(windows.shape[2]):
                            header.append(f"feat_{i}")
                        f.write(",".join(header) + "\n")

                        # 각 엔트리의 마지막 프레임(가장 최근 키포인트) 데이터를 CSV로 저장
                        for i, e in enumerate(self._entries):
                            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e["timestamp"]))
                            row = [str(i), f"{e['timestamp']:.6f}", dt, str(e["label_id"]), e["word"]]
                            # 마지막 프레임의 키포인트 데이터 추가 (274차원)
                            last_frame_keypoints = e["window"][-1]  # 마지막 프레임
                            for kp in last_frame_keypoints:
                                row.append(f"{kp:.6f}")
                            f.write(",".join(row) + "\n")
                    logger.info(f"키포인트 CSV 저장: {keypoints_csv_path}")
                except Exception as e:
                    logger.error(f"키포인트 CSV 저장 실패: {e}")
        except Exception as e:
            logger.error(f"추론 로그 저장 실패: {e}")
