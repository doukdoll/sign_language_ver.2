// 팝업 배경 어둡게 처리

export default function Dimmed({ onClick }: { onClick?: () => void }) {
  return (
    <div
      className="fixed inset-0 bg-black/40 z-40"
      onClick={onClick}
    />
  );
}
