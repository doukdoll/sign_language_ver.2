interface RecognitionButtonsProps {
  onRetry: () => void;
  onConfirm: () => void;
}

export default function RecognitionButtons({ onRetry, onConfirm }: RecognitionButtonsProps) {
  return (
    <div className="flex gap-4">
      <button
        onClick={onRetry}
        className="px-9 py-2.5 bg-white border border-blue-300 text-blue-600 font-semibold rounded-xl 
                   hover:bg-sky-50 active:scale-95 transition-all duration-150"
      >
        다시 인식하기
      </button>
      <button
        onClick={onConfirm}
        className="px-9 py-2.5 bg-blue-500 text-white font-semibold rounded-xl 
                   hover:bg-blue-600 active:scale-95 transition-all duration-150"
      >
        맞아요
      </button>
    </div>
  );
}
