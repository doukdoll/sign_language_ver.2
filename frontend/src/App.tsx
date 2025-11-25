import { createBrowserRouter, RouterProvider } from "react-router-dom";
import HomePage from "./pages/HomePage";
import NotFoundPage from "./pages/NotFoundPage";
import TripTypePage from "./pages/TripTypePage";
import DateTimePage from "./pages/DateTimePage";
import PassengerPage from "./pages/PassengerPage";
import TrainTimeTablePage from "./pages/TrainTimeTablePage";
import SeatPage from "./pages/SeatPage";
import DeparturePage from "./pages/DeparturePage";
import ArrivalPage from "./pages/ArrivalPage";
import ReservationSummaryPage from "./pages/ReservationSummaryPage";


const router = createBrowserRouter([
  { path: "/", element: <HomePage />, errorElement: <NotFoundPage /> },
  { path: "/departure", element: <DeparturePage /> },
  { path: "/arrival", element: <ArrivalPage /> },
  { path: "/passenger", element: <PassengerPage /> },
  { path: "/triptype", element: <TripTypePage/>},
  { path: "/datetime", element: <DateTimePage/>},
  { path: "/timetable", element: <TrainTimeTablePage /> },
  { path: "/seat", element: <SeatPage/>},
  { path: "/summary", element: <ReservationSummaryPage/>},
  { path: "/"}
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
