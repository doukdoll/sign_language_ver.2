interface RecognitionButtonsProps {
  onRetry: () => void;
  onConfirm: () => void;
}

export default function RecognitionButtons({ onRetry, onConfirm }: RecognitionButtonsProps) {
  return (
    <div className="flex gap-4 w-full h-full">
      
      
      <button
        onClick={onRetry}
        className="flex-1 h-full bg-white border-2 border-blue-300 text-blue-600 text-lg font-bold rounded-2xl 
                   hover:bg-sky-50 active:scale-95 transition-all duration-150 shadow-sm"
      >
        ↺ 다시 인식하기
      </button>

      
      <button
        onClick={onConfirm}
        className="flex-1 h-full bg-blue-500 text-white text-xl font-bold rounded-2xl 
                   hover:bg-blue-600 active:scale-95 transition-all duration-150 shadow-md"
      >
        맞아요
      </button>
      
    </div>
  );
}