import homeIcon from "../assets/home.png";
import backIcon from "../assets/angle-right.png"


interface HeaderProps {
  title: string;
  onBack?: () => void;
  onHome?: () => void;
}

const Header = ({ title, onBack, onHome }: HeaderProps) => {
  return (
    <div
      style={{
        width: "100%",
        maxWidth: "400px",
        height: "30px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        backgroundColor: "#dbeafe",
        borderRadius: "4px",
        padding: "8px 12px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        position: "relative",
      }}
    >
      {/* 좌측 뒤로가기 */}
      <img
        src={backIcon}
        alt="뒤로가기"
        style={{ width: "20px", height: "20px", cursor: "pointer" }}
        onClick={onBack}
      />

      {/* 중앙 텍스트 */}
      <span
        style={{
          fontSize: "12px",
          color: "#9ca3af",
          position: "absolute",
          left: "50%",
          transform: "translateX(-50%)",
        }}
      >
        {title}
      </span>

      {/* 우측 홈 */}
      <img
        src={homeIcon}
        alt="홈"
        style={{ width: "20px", height: "20px", cursor: "pointer" }}
        onClick={onHome}
      />
    </div>
  );
};

export default Header;


