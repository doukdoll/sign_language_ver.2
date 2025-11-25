import json
import numpy as np
import os
import glob
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from scipy.interpolate import interp1d
from functools import lru_cache
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BodyPartNormalizationProcessor:
    """
    신체 부위별 정규화를 적용한 키포인트 처리기
    
    핵심 개선사항:
    - Pose: 전체 화면 기준 정규화 (기존 방식)
    - Face: 얼굴 바운딩 박스 기준 정규화 (디테일 강화)
    - Hands: 각 손의 바운딩 박스 기준 정규화 (수어 핵심 동작 강화)
    """
    
    # 클래스 상수
    POSE_KEYPOINTS = 25
    FACE_KEYPOINTS = 70
    HAND_KEYPOINTS = 21
    TOTAL_KEYPOINTS = POSE_KEYPOINTS + FACE_KEYPOINTS + (HAND_KEYPOINTS * 2)
    
    # 키포인트 매핑
    KEYPOINT_PARTS = ('pose_keypoints_2d', 'face_keypoints_2d', 
                     'hand_left_keypoints_2d', 'hand_right_keypoints_2d')
    KEYPOINT_COUNTS = (POSE_KEYPOINTS, FACE_KEYPOINTS, HAND_KEYPOINTS, HAND_KEYPOINTS)
    
    def __init__(self, image_width: int = 1920, image_height: int = 1080, 
                 target_frames: int = 180, target_batch_size: int = 15,
                 enable_multiprocessing: bool = True, max_workers: int = None,
                 confidence_threshold: float = 0.3, bbox_padding: float = 0.1):
        """
        신체 부위별 정규화 처리기 초기화
        
        Args:
            image_width: 원본 이미지 너비 (기본값)
            image_height: 원본 이미지 높이 (기본값)
            target_frames: 목표 프레임 수
            target_batch_size: 목표 배치 사이즈
            enable_multiprocessing: 멀티프로세싱 활성화 여부
            max_workers: 최대 워커 수
            confidence_threshold: 유효한 키포인트 판별 임계값 (confidence)
            bbox_padding: 바운딩 박스 패딩 비율 (0.1 = 10%)
        """
        self.image_width = image_width
        self.image_height = image_height
        self.target_frames = target_frames
        self.target_batch_size = target_batch_size
        self.enable_multiprocessing = enable_multiprocessing
        self.max_workers = max_workers or min(8, os.cpu_count() or 1)
        self.confidence_threshold = confidence_threshold
        self.bbox_padding = bbox_padding
        
        # 정규화 상수 미리 계산
        self.inv_width = 1.0 / image_width
        self.inv_height = 1.0 / image_height
        
        logger.info(f"=== 신체 부위별 정규화 프로세서 초기화 ===")
        logger.info(f"키포인트 구성: Pose({self.POSE_KEYPOINTS}) + Face({self.FACE_KEYPOINTS}) + "
                   f"Hands({self.HAND_KEYPOINTS}×2) = {self.TOTAL_KEYPOINTS}")
        logger.info(f"Confidence 임계값: {confidence_threshold}")
        logger.info(f"바운딩 박스 패딩: {bbox_padding * 100}%")
        logger.info(f"멀티프로세싱: {'활성화' if enable_multiprocessing else '비활성화'} "
                   f"(최대 워커: {self.max_workers})")
    
    @lru_cache(maxsize=128)
    def _load_json_cached(self, json_path: str) -> str:
        """JSON 파일 캐싱 로드"""
        with open(json_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def load_keypoints(self, json_path: str) -> Dict:
        """JSON 파일에서 키포인트 데이터 로드"""
        try:
            json_str = self._load_json_cached(json_path)
            return json.loads(json_str)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"JSON 로드 실패: {json_path} - {e}")
            raise
    
    def extract_2d_keypoints_vectorized(self, data: Dict) -> np.ndarray:
        """
        벡터화된 2D 키포인트 추출
        
        Returns:
            shape: (total_keypoints, 3) - 모든 키포인트를 하나의 배열로
        """
        people_data = data['people']
        
        # 모든 키포인트를 한 번에 처리
        keypoints_list = []
        for part_name, count in zip(self.KEYPOINT_PARTS, self.KEYPOINT_COUNTS):
            keypoint_data = np.array(people_data[part_name], dtype=np.float32)
            keypoints_list.append(keypoint_data.reshape(count, 3))
        
        # 한 번에 concatenate
        return np.vstack(keypoints_list)
    
    def _extract_resolution_from_json(self, data: Dict) -> Optional[Tuple[float, float]]:
        """JSON 메타데이터에서 프레임 해상도 추출"""
        candidates = [
            ("canvas_width", "canvas_height"),
            ("canvasWidth", "canvasHeight"),
            ("image_width", "image_height"),
            ("width", "height"),
            ("w", "h"),
        ]
        for w_key, h_key in candidates:
            w = data.get(w_key)
            h = data.get(h_key)
            if isinstance(w, (int, float)) and isinstance(h, (int, float)) and w > 1 and h > 1:
                return float(w), float(h)
        
        canvas = data.get("canvas_size") or data.get("canvasSize") or data.get("frame_size")
        if isinstance(canvas, (list, tuple)) and len(canvas) >= 2:
            w, h = canvas[0], canvas[1]
            if isinstance(w, (int, float)) and isinstance(h, (int, float)) and w > 1 and h > 1:
                return float(w), float(h)
        if isinstance(canvas, dict):
            w = canvas.get("width") or canvas.get("w")
            h = canvas.get("height") or canvas.get("h")
            if isinstance(w, (int, float)) and isinstance(h, (int, float)) and w > 1 and h > 1:
                return float(w), float(h)
        return None
    
    def _estimate_resolution_from_keypoints(self, keypoints: np.ndarray) -> Optional[Tuple[float, float]]:
        """키포인트 좌표의 최대값으로부터 해상도 추정"""
        if keypoints is None or keypoints.size == 0:
            return None
        try:
            xs = keypoints[:, 0]
            ys = keypoints[:, 1]
            x_max = float(np.nanmax(xs)) if np.isfinite(xs).any() else float("nan")
            y_max = float(np.nanmax(ys)) if np.isfinite(ys).any() else float("nan")
            if np.isfinite(x_max) and np.isfinite(y_max) and x_max > 1.0 and y_max > 1.0:
                return x_max, y_max
        except Exception:
            pass
        return None
    
    def _resolve_frame_resolution(self, data: Dict, keypoints: np.ndarray) -> Tuple[float, float]:
        """프레임별 해상도 결정"""
        meta_res = self._extract_resolution_from_json(data)
        if meta_res is not None:
            return meta_res
        est_res = self._estimate_resolution_from_keypoints(keypoints)
        if est_res is not None:
            return est_res
        return float(self.image_width), float(self.image_height)
    
    def normalize_keypoints_by_bodypart(self, keypoints: np.ndarray, *, width: float, height: float) -> np.ndarray:
        """
        ★★★ 핵심 메서드: 신체 부위별 차별화된 정규화 ★★★
        
        Args:
            keypoints: (137, 3) 형태의 키포인트 배열 (x, y, confidence)
            width: 프레임의 가로 해상도
            height: 프레임의 세로 해상도
        
        Returns:
            정규화된 키포인트 배열
            
        Keypoint 구조:
        - Pose (0-24): 25개 포즈 키포인트
        - Face (25-94): 70개 얼굴 키포인트
        - Left Hand (95-115): 21개 왼손 키포인트
        - Right Hand (116-136): 21개 오른손 키포인트
        """
        normalized = keypoints.copy()
        w = float(width) if width and width > 0 else float(self.image_width)
        h = float(height) if height and height > 0 else float(self.image_height)
        
        # === 1. Pose: 전체 화면 기준 정규화 (기존 방식 유지) ===
        pose_kps = keypoints[0:25]
        normalized[0:25, 0] = pose_kps[:, 0] / w
        normalized[0:25, 1] = pose_kps[:, 1] / h
        # confidence는 그대로 유지
        
        # === 2. Face: 얼굴 바운딩 박스 기준 정규화 ===
        face_kps = keypoints[25:95]
        face_valid = face_kps[:, 2] > self.confidence_threshold
        
        if face_valid.sum() >= 5:  # 최소 5개 이상 감지되어야 신뢰 가능
            valid_face = face_kps[face_valid]
            face_x_min, face_x_max = valid_face[:, 0].min(), valid_face[:, 0].max()
            face_y_min, face_y_max = valid_face[:, 1].min(), valid_face[:, 1].max()
            
            # 바운딩 박스에 패딩 추가 (경계 잘림 방지)
            face_w = max(face_x_max - face_x_min, 1.0)
            face_h = max(face_y_max - face_y_min, 1.0)
            face_x_min -= face_w * self.bbox_padding
            face_y_min -= face_h * self.bbox_padding
            face_w *= (1.0 + 2 * self.bbox_padding)
            face_h *= (1.0 + 2 * self.bbox_padding)
            
            # 정규화: 얼굴 영역을 [0, 1] 범위로 확장
            normalized[25:95, 0] = (face_kps[:, 0] - face_x_min) / face_w
            normalized[25:95, 1] = (face_kps[:, 1] - face_y_min) / face_h
            
            logger.debug(f"얼굴 정규화 적용: bbox_w={face_w:.1f}, bbox_h={face_h:.1f}")
        else:
            # 얼굴 감지 실패 시 전체 화면 기준 (fallback)
            normalized[25:95, 0] = face_kps[:, 0] / w
            normalized[25:95, 1] = face_kps[:, 1] / h
            logger.debug("얼굴 감지 실패 → 전체 화면 기준 정규화")
        
        # === 3. Left Hand: 왼손 바운딩 박스 기준 정규화 ===
        left_hand_kps = keypoints[95:116]
        left_hand_valid = left_hand_kps[:, 2] > self.confidence_threshold
        
        if left_hand_valid.sum() >= 5:
            valid_left = left_hand_kps[left_hand_valid]
            lh_x_min, lh_x_max = valid_left[:, 0].min(), valid_left[:, 0].max()
            lh_y_min, lh_y_max = valid_left[:, 1].min(), valid_left[:, 1].max()
            
            lh_w = max(lh_x_max - lh_x_min, 1.0)
            lh_h = max(lh_y_max - lh_y_min, 1.0)
            lh_x_min -= lh_w * self.bbox_padding
            lh_y_min -= lh_h * self.bbox_padding
            lh_w *= (1.0 + 2 * self.bbox_padding)
            lh_h *= (1.0 + 2 * self.bbox_padding)
            
            normalized[95:116, 0] = (left_hand_kps[:, 0] - lh_x_min) / lh_w
            normalized[95:116, 1] = (left_hand_kps[:, 1] - lh_y_min) / lh_h
            
            logger.debug(f"왼손 정규화 적용: bbox_w={lh_w:.1f}, bbox_h={lh_h:.1f}")
        else:
            normalized[95:116, 0] = left_hand_kps[:, 0] / w
            normalized[95:116, 1] = left_hand_kps[:, 1] / h
            logger.debug("왼손 감지 실패 → 전체 화면 기준 정규화")
        
        # === 4. Right Hand: 오른손 바운딩 박스 기준 정규화 ===
        right_hand_kps = keypoints[116:137]
        right_hand_valid = right_hand_kps[:, 2] > self.confidence_threshold
        
        if right_hand_valid.sum() >= 5:
            valid_right = right_hand_kps[right_hand_valid]
            rh_x_min, rh_x_max = valid_right[:, 0].min(), valid_right[:, 0].max()
            rh_y_min, rh_y_max = valid_right[:, 1].min(), valid_right[:, 1].max()
            
            rh_w = max(rh_x_max - rh_x_min, 1.0)
            rh_h = max(rh_y_max - rh_y_min, 1.0)
            rh_x_min -= rh_w * self.bbox_padding
            rh_y_min -= rh_h * self.bbox_padding
            rh_w *= (1.0 + 2 * self.bbox_padding)
            rh_h *= (1.0 + 2 * self.bbox_padding)
            
            normalized[116:137, 0] = (right_hand_kps[:, 0] - rh_x_min) / rh_w
            normalized[116:137, 1] = (right_hand_kps[:, 1] - rh_y_min) / rh_h
            
            logger.debug(f"오른손 정규화 적용: bbox_w={rh_w:.1f}, bbox_h={rh_h:.1f}")
        else:
            normalized[116:137, 0] = right_hand_kps[:, 0] / w
            normalized[116:137, 1] = right_hand_kps[:, 1] / h
            logger.debug("오른손 감지 실패 → 전체 화면 기준 정규화")
        
        return normalized
    
    def convert_to_relative_vectorized(self, keypoints: np.ndarray) -> np.ndarray:
        """
        벡터화된 상대 위치 변환 (코 기준)
        
        주의: 신체 부위별 정규화 후에는 각 부위가 이미 독립적으로 정규화되었으므로,
        상대 위치 변환이 필요 없을 수 있습니다. 필요시 부위별로 다르게 적용해야 합니다.
        
        현재는 Pose 부분만 코 기준 상대 좌표로 변환합니다.
        """
        # 코(nose) 위치 찾기 (첫 번째 키포인트)
        nose_keypoint = keypoints[0]
        
        if nose_keypoint[2] <= 0:  # confidence 체크
            logger.warning("코(nose) 키포인트의 confidence가 0입니다.")
            return keypoints
        
        # Pose 부분만 상대 위치로 변환 (0-24)
        relative_keypoints = keypoints.copy()
        relative_keypoints[0:25, :2] -= nose_keypoint[:2]
        
        # Face, Hands는 이미 바운딩 박스 기준으로 정규화되었으므로 그대로 유지
        
        return relative_keypoints
    
    def process_single_frame_optimized(self, json_path: str) -> np.ndarray:
        """
        최적화된 단일 프레임 처리 (신체 부위별 정규화 적용)
        
        Returns:
            shape: (total_keypoints, 2) - x, y 좌표만
        """
        # 1. 키포인트 로드
        data = self.load_keypoints(json_path)
        keypoints = self.extract_2d_keypoints_vectorized(data)
        
        # 2. 프레임 해상도 결정
        frame_w, frame_h = self._resolve_frame_resolution(data, keypoints)
        
        # 3. ★★★ 신체 부위별 정규화 적용 ★★★
        normalized = self.normalize_keypoints_by_bodypart(keypoints, width=frame_w, height=frame_h)
        
        # 4. 상대 위치 변환 (Pose만 적용)
        relative = self.convert_to_relative_vectorized(normalized)
        
        # 5. x, y 좌표만 반환
        return relative[:, :2]
    
    def resample_sequence_optimized(self, keypoints_sequence: np.ndarray) -> np.ndarray:
        """
        최적화된 시퀀스 리샘플링
        
        Args:
            keypoints_sequence: shape (original_frames, keypoints, 2)
            
        Returns:
            shape: (target_frames, keypoints, 2)
        """
        original_frames = keypoints_sequence.shape[0]
        
        if original_frames == self.target_frames:
            return keypoints_sequence
        
        # 벡터화된 보간
        original_indices = np.linspace(0, original_frames - 1, original_frames)
        target_indices = np.linspace(0, original_frames - 1, self.target_frames)
        
        flat_sequence = keypoints_sequence.reshape(original_frames, -1)
        
        interpolator = interp1d(original_indices, flat_sequence, 
                              kind='linear', axis=0, 
                              bounds_error=False, fill_value='extrapolate')
        
        resampled_flat = interpolator(target_indices)
        
        return resampled_flat.reshape(self.target_frames, self.TOTAL_KEYPOINTS, 2)
    
    def process_json_files_batch(self, json_files: List[str]) -> List[np.ndarray]:
        """
        배치 JSON 파일 처리 (멀티프로세싱 지원)
        """
        if not self.enable_multiprocessing or len(json_files) < 4:
            return [self.process_single_frame_optimized(json_file) 
                   for json_file in json_files]
        
        keypoints_list = [None] * len(json_files)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_index = {
                executor.submit(self.process_single_frame_optimized, json_files[i]): i 
                for i in range(len(json_files))
            }
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    keypoints_list[index] = future.result()
                except Exception as e:
                    logger.error(f"프레임 처리 실패 (인덱스 {index}): {e}")
                    keypoints_list[index] = np.zeros((self.TOTAL_KEYPOINTS, 2), dtype=np.float32)
        
        return keypoints_list
    
    def find_json_files_sorted(self, root_dir: str) -> Dict[str, List[str]]:
        """최적화된 JSON 파일 찾기 및 정렬"""
        folder_json_map = {}
        
        try:
            subdirs = [d for d in os.listdir(root_dir) 
                      if os.path.isdir(os.path.join(root_dir, d))]
        except OSError as e:
            logger.error(f"디렉토리 읽기 실패: {root_dir} - {e}")
            return {}
        
        for subdir in subdirs:
            subdir_path = os.path.join(root_dir, subdir)
            json_pattern = os.path.join(subdir_path, "*_keypoints.json")
            json_files = glob.glob(json_pattern)
            
            if json_files:
                def extract_frame_number(filepath):
                    try:
                        return int(os.path.basename(filepath).split('_')[-2])
                    except (ValueError, IndexError):
                        return 0
                
                json_files.sort(key=extract_frame_number)
                folder_json_map[subdir] = json_files
                logger.info(f"폴더 '{subdir}': {len(json_files)}개 JSON 파일")
        
        logger.info(f"총 {len(folder_json_map)}개 폴더에서 JSON 파일 발견")
        return folder_json_map
    
    def process_video_sequence_optimized(self, json_files: List[str]) -> np.ndarray:
        """
        최적화된 비디오 시퀀스 처리
        
        Returns:
            shape: (target_frames, keypoints*2) - 평탄화된 시퀀스
        """
        keypoints_list = self.process_json_files_batch(json_files)
        
        valid_keypoints = [kp for kp in keypoints_list if kp is not None]
        
        if not valid_keypoints:
            raise ValueError("유효한 키포인트가 없습니다.")
        
        keypoints_sequence = np.stack(valid_keypoints, axis=0)
        
        resampled = self.resample_sequence_optimized(keypoints_sequence)
        
        return resampled.reshape(self.target_frames, -1)
    
    def create_csv_optimized(self, tensor: np.ndarray, folder_name: str, 
                           output_dir: str) -> Dict[str, str]:
        """
        최적화된 CSV 생성
        """
        os.makedirs(output_dir, exist_ok=True)
        
        if not hasattr(self, '_csv_columns'):
            self._csv_columns = ['frame'] + [
                f"keypoint_{i}_{coord}" 
                for i in range(self.TOTAL_KEYPOINTS) 
                for coord in ['x', 'y']
            ]
        
        data_dict = {'frame': range(1, self.target_frames + 1)}
        
        for i, col in enumerate(self._csv_columns[1:]):
            data_dict[col] = tensor[:, i]
        
        df = pd.DataFrame(data_dict)
        
        csv_filename = f"{folder_name}_bodypart_norm.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        df.to_csv(csv_path, index=False, float_format='%.6f')  # 정밀도 증가
        
        logger.info(f"CSV 저장: {csv_filename} - {tensor.shape}")
        
        return {
            'csv_file': csv_filename,
            'csv_path': csv_path,
            'shape': tensor.shape
        }
    
    def process_single_video_optimized(self, video_folder_path: str, 
                                     output_dir: str = "bodypart_norm_output") -> Dict:
        """
        최적화된 단일 비디오 처리
        """
        logger.info(f"=== 신체 부위별 정규화 비디오 처리 시작 ===")
        logger.info(f"폴더: {video_folder_path}")
        
        json_pattern = os.path.join(video_folder_path, "*_keypoints.json")
        json_files = glob.glob(json_pattern)
        
        if not json_files:
            raise ValueError(f"JSON 파일을 찾을 수 없습니다: {video_folder_path}")
        
        json_files.sort(key=lambda x: int(os.path.basename(x).split('_')[-2]))
        
        folder_name = os.path.basename(video_folder_path)
        logger.info(f"처리할 프레임: {len(json_files)}개 → {self.target_frames}개로 리샘플링")
        
        tensor = self.process_video_sequence_optimized(json_files)
        
        csv_info = self.create_csv_optimized(tensor, folder_name, output_dir)
        
        result = {
            **csv_info,
            'original_frames': len(json_files),
            'resampled_frames': self.target_frames,
            'folder_name': folder_name,
            'normalization_method': 'bodypart_bbox'
        }
        
        logger.info("=== 처리 완료 ===")
        return result


def process_video_with_bodypart_norm(video_folder_path: str, 
                                     output_dir: str = "bodypart_norm_output",
                                     **kwargs) -> Dict:
    """
    신체 부위별 정규화를 사용한 비디오 처리 함수 (편의 함수)
    """
    processor = BodyPartNormalizationProcessor(**kwargs)
    return processor.process_single_video_optimized(video_folder_path, output_dir)


def main():
    """메인 함수 - 예제 사용법"""
    # 설정
    word_folder_path = "Source_data/9.슬프다"  # 처리할 단어 폴더 경로
    output_dir = "bodypart_norm_output"  # 신체 부위별 정규화 결과 저장 경로
    
    if not os.path.exists(word_folder_path):
        logger.error(f"단어 폴더를 찾을 수 없습니다: {word_folder_path}")
        return
    
    try:
        video_folders = [
            os.path.join(word_folder_path, d)
            for d in os.listdir(word_folder_path)
            if os.path.isdir(os.path.join(word_folder_path, d))
        ]
    except OSError as e:
        logger.error(f"단어 폴더 읽기 오류: {e}")
        return
    
    if not video_folders:
        logger.info(f"'{word_folder_path}' 내에 처리할 비디오 폴더가 없습니다.")
        return
    
    logger.info(f"'{word_folder_path}' 에서 {len(video_folders)}개의 비디오 폴더 처리 시작")
    
    all_results = []
    for video_folder_path_item in video_folders:
        logger.info(f"--- '{os.path.basename(video_folder_path_item)}' 처리 시작 ---")
        try:
            result = process_video_with_bodypart_norm(
                video_folder_path=video_folder_path_item,
                output_dir=output_dir,
                enable_multiprocessing=True,
                max_workers=4,
                confidence_threshold=0.3,  # confidence 임계값
                bbox_padding=0.1  # 바운딩 박스 패딩 10%
            )
            
            if result:
                logger.info(f"--- '{os.path.basename(video_folder_path_item)}' 처리 완료 ---")
                logger.info(f"  CSV 파일: {result.get('csv_path', 'N/A')}")
                all_results.append(result)
        except ValueError as ve:
            logger.error(f"'{os.path.basename(video_folder_path_item)}' 처리 중 값 오류: {ve}")
        except Exception as e:
            logger.error(f"'{os.path.basename(video_folder_path_item)}' 처리 중 예상치 못한 오류: {e}", 
                        exc_info=True)
    
    logger.info(f"=== 총 {len(all_results)}개의 비디오 폴더 처리 완료 ===")
    if all_results:
        logger.info("생성된 CSV 파일 목록:")
        for res in all_results:
            logger.info(f"  - {res.get('csv_path', 'N/A')}")


if __name__ == "__main__":
    main()

