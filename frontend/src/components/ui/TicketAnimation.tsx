// src/components/ui/TicketOutputAnimation.tsx
import React from 'react';
import ticketIcon from '../icons/trainticket.png';

const TicketOutputAnimation: React.FC = () => {
    const floatingAnimationStyles = `
        @keyframes floating {
            0% { transform: translateY(0px); }
            50% { transform: translateY(8px); }
            100% { transform: translateY(0px); }
        }
    `;

    return (
        <div className="flex flex-col items-center relative mt-4">
            <style>{floatingAnimationStyles}</style>

            {/* 출력구 바 */}
            <div className="w-[180px] h-3 bg-gray-900 relative z-10 shadow-sm"></div>

            {/* 티켓 */}
            <img
                src={ticketIcon}
                alt="KTX 승차권"
                className="relative z-0 -mt-6 translate-x-4" 
                style={{
                    width: '200px',   // 출력구와 가로폭 동일하게
                    animation: 'floating 2s ease-in-out infinite'
                }}
            />
        </div>
    );
};

export default TicketOutputAnimation;
