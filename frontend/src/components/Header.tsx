import HomeIcon from "./icons/HomeIcon";
import BackIcon from "./icons/BackIcon";
import { useNavigate } from "react-router-dom";

interface HeaderProps {
  title: string;
}


export default function Header({ title }: HeaderProps) {

  const navigate = useNavigate();

  // 뒤로가기
  const handleBack = () => { navigate(-1); };

  // 홈 이동
  const handleHome = () => { navigate("/");};


  return (
    <header className="bg-blue-50 w-full h-16 shadow-sm relative">
      <button
      onClick={handleBack}
      className="absolute left-4 top-1/2 -translate-y-1/2">
        <BackIcon/>
      </button>
      
     
      <h1 className="text-center font-bold text-lg mt-4">{title}</h1>
      
     
      <button 
      onClick={handleHome}
      className="absolute right-4 top-1/2 -translate-y-1/2">
        <HomeIcon/>
      </button>
    </header>
  );
}