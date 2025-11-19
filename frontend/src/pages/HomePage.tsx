import { useState, useRef } from "react";
import ticketIcon from "../assets/ticket.png";
import { useNavigate} from "react-router-dom";

export default function HomePage() {
  const [isRecognized, setIsRecognized] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const navigate = useNavigate();

  const handleStart = () => {
    navigate("/departure"); // 출발역 화면으로 이동
  };

  return (
    <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
      
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl shadow-2xl flex flex-col overflow-hidden">
              
        <main className="flex flex-col items-center justify-center  flex-1 px-8 text-center">
          <p className="text-[27px] font-bold text-gray-800 leading-snug mb-4">
            수어로 간편하게 <br />
            기차표를 예매하세요.
          </p>
           <button
            onClick={handleStart}
            className="flex items-center justify-center gap-3 bg-[#60A5FA]  border-blue-400 active:scale-95 hover:bg-blue-600 text-white font-bold text-2xl px-12 py-6 rounded shadow-lg transition-all duration-200"
          >
            <img src={ticketIcon} alt="ticket" className="w-8 h-8" />
            예매 시작하기
          </button>
          <p className="text-lg font-medium text-gray-500 mt-6">
            시작하기 버튼을 눌러주세요.
          </p>
        </main>

        
        <footer className="py-10 text-center bg-gray-50 border-t border-gray-200">
         
        </footer>
      </div>
    </div>
  );
}