import axios from "axios";

const instance = axios.create({
  baseURL: "http://localhost:8080/api", // 백엔드 서버 주소
});

// 인식 요청 함수 
export const recognizeSignLanguage = async (
  recognitionTarget: string,
  signLanguageData: string
) => {
  const res = await instance.post(`/signlanguage/recognize/${recognitionTarget}`, {
    signLanguageData,
    recognitionTarget,
  });
  return res.data;
};

// 탑승 인원
export const setPassengers = async (passengers: number) => {
  const res = await instance.post("/signlanguage/recognize/passengers", {
    signLanguageData: passengers.toString(),
    recognitionTarget: "passengers"
  });
  return res.data;
};

// 왕복/편도
export const setTripType = async (tripType: string) => {
  const res = await instance.post("/signlanguage/recognize/triptype", {
    signLanguageData: tripType,
    recognitionTarget: "triptype",
  });
  return res.data; 
};


// 날짜/시간
export const setDateTime = async (data: string) => {
  const res = await instance.post("/signlanguage/recognize/datetime", {
    signLanguageData: data,
    recognitionTarget: "datetime",
  });
  return res.data;
};


export default instance;