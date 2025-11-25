import axios from "axios";

const instance = axios.create({
  baseURL: "http://localhost:8080/api", // 백엔드 서버 주소
});

<<<<<<< HEAD
// 인식 요청 함수 
=======

>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
export const recognizeSignLanguage = async (
  recognitionTarget: string,
  signLanguageData: string
) => {
<<<<<<< HEAD
  const res = await instance.post(`/signlanguage/recognize/${recognitionTarget}`, {
    signLanguageData,
=======
  const res = await instance.post(`/signlanguage/recognize`, { 
    signLanguageData, // ⚠️ DTO 필드명이 'keypoints'라면 수정 필요 (아래 설명 참고)
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
    recognitionTarget,
  });
  return res.data;
};

<<<<<<< HEAD
// 탑승 인원
export const setPassengers = async (passengers: number) => {
  const res = await instance.post("/signlanguage/recognize/passengers", {
    signLanguageData: passengers.toString(),
=======
// 2. 탑승 인원 (수정됨)
export const setPassengers = async (passengers: number) => {
  const res = await instance.post("/signlanguage/passengers", {
    signLanguageData: passengers.toString(), 
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
    recognitionTarget: "passengers"
  });
  return res.data;
};

<<<<<<< HEAD
// 왕복/편도
export const setTripType = async (tripType: string) => {
  const res = await instance.post("/signlanguage/recognize/triptype", {
=======
// 3. 왕복/편도 (수정됨)
export const setTripType = async (tripType: string) => {
  const res = await instance.post("/signlanguage/triptype", {
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
    signLanguageData: tripType,
    recognitionTarget: "triptype",
  });
  return res.data; 
};

<<<<<<< HEAD

// 날짜/시간
export const setDateTime = async (data: string) => {
  const res = await instance.post("/signlanguage/recognize/datetime", {
=======
// 4. 날짜/시간 (수정됨)
export const setDateTime = async (data: string) => {
  const res = await instance.post("/signlanguage/datetime", {
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
    signLanguageData: data,
    recognitionTarget: "datetime",
  });
  return res.data;
};

<<<<<<< HEAD

=======
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
export default instance;