import axios from "axios";

const instance = axios.create({
  baseURL: "http://localhost:8080/api", // 백엔드 서버 주소
});


export const recognizeSignLanguage = async (
  recognitionTarget: string,
  signLanguageData: string
) => {
  const res = await instance.post(`/signlanguage/recognize`, { 
    signLanguageData, // ⚠️ DTO 필드명이 'keypoints'라면 수정 필요 (아래 설명 참고)
    recognitionTarget,
  });
  return res.data;
};

// 2. 탑승 인원 (수정됨)
export const setPassengers = async (passengers: number) => {
  const res = await instance.post("/signlanguage/passengers", {
    signLanguageData: passengers.toString(), 
    recognitionTarget: "passengers"
  });
  return res.data;
};

// 3. 왕복/편도 (수정됨)
export const setTripType = async (tripType: string) => {
  const res = await instance.post("/signlanguage/triptype", {
    signLanguageData: tripType,
    recognitionTarget: "triptype",
  });
  return res.data; 
};

// 4. 날짜/시간 (수정됨)
export const setDateTime = async (data: string) => {
  const res = await instance.post("/signlanguage/datetime", {
    signLanguageData: data,
    recognitionTarget: "datetime",
  });
  return res.data;
};

export default instance;