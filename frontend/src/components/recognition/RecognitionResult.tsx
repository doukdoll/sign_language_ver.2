import checkIcon from "../icons/check.png";
interface RecognitionResultProps {
  stationName: string;
}

function RecognitionResult({ stationName }: RecognitionResultProps) {
  return (
    <div className="w-[100%] bg-green-50 border border-green-300 rounded-xl py-3 px-4 mb-4 shadow-sm text-left">
      <p className="text-[16px] text-green-700 font-semibold flex items-center gap-2">
        <img src={checkIcon} alt="인식 완료" className="w-5 h-5" />
        {stationName} 인식 완료
      </p>
      <p className="text-gray-600 text-[14px] mt-1">인식된 결과가 맞나요?</p>
    </div>
  );
}

export default RecognitionResult;
