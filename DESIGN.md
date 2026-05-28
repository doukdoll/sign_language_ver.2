# DESIGN.md - Sign Language Transport Platform

This document outlines the design principles, visual identity, and component architecture for the Sign Language Transport Platform. This file is intended to provide context for UI/UX improvements and design consistency tools like Google Stitch.

---

## 🎨 Visual Identity

### 1. Color Palette
- **Primary Blue:** `#2260f5` (Main brand color, primary buttons)
- **Secondary Blue:** `#60A5FA` (Lighter UI accents, secondary buttons)
- **Backgrounds:**
  - Base: `#F2F4F8` (Light gray-blue for the app container)
  - Surface: `#FFFFFF` (White for cards and content areas)
  - Gradients: `blue-50` to `white` (Used in page backgrounds)
- **Typography & UI:**
  - Heading Text: `#3b4252` (Dark navy for readability)
  - Body/Subtext: `#6b7280` (Medium gray)
  - Status/Highlight: `#3b4252` (Emphasis color)

### 2. Typography
- **Primary Font:** Sans-serif (Clean, modern, highly legible)
- **Styles:**
  - **Main Headers:** 40px - 55px, Weight 800 (Extra Bold)
  - **Section Titles:** 23px - 27px, Weight 700 (Bold)
  - **Body Text:** 18px - 30px, Weight 400/500 (Regular/Medium)
  - **Status Text:** 30px - 40px, Weight 700

### 3. Layout & Shape
- **Form Factor:** Optimized for **Kiosk Portrait Mode** (Target resolution aspect: ~9:18).
- **Core Container:** 450px (width) x 900px (height) with a `shadow-2xl` and `border-radius: 20px`.
- **Spacing:** Generous padding (`px-8`, `px-10`) to ensure a touch-friendly interface.
- **Rounding:** Large border-radii (20px to 60px) for a soft, modern, and friendly feel.

---

## 🧱 Component Architecture

### 1. Common Components
- **Header:** Sticky top navigation with "Back" and "Home" icons, centering the current page title.
- **Footer:** Navigation or call-to-action buttons (e.g., "Next", "Confirm").
- **TrainCard:** Displays individual train schedules with departure/arrival times, duration, and price.

### 2. Recognition Components (Core Feature)
- **CameraFeed:** A large, rounded video frame (typically 900px height scaled into the container) that captures user sign language.
- **RecognitionResult:** An overlay or immediate sub-component that displays the recognized word (e.g., "서울역") in real-time.
- **RecognitionButtons:** "Retry" and "Confirm" actions presented after a word is successfully detected.

### 3. Functional Modules
- **SeatGrid:** A visual map of the train car for seat selection.
- **PaymentPopup/Process:** Guided step-by-step payment simulation.

---

## ✨ Motion & Interaction
- **Button Feedback:** `active:scale-95` and transition effects (`duration-200`) provide tactile feedback for touch screens.
- **Transitions:** Simple `FadeIn` / `FadeOut` animations for page transitions and result displays to prevent jarring UI jumps.
- **Accessibility:** Large touch targets (buttons are often `py-6` or `px-12`) designed for kiosk interaction.

---

## 🚉 User Flow (Design Perspective)
1. **Home:** High-impact call to action ("예매 시작하기").
2. **Step-by-Step Selection:** Each step (Departure -> Arrival -> Date -> Passengers -> Train -> Seat) follows a consistent layout:
   - Header with Progress Title.
   - Instructional text at the top.
   - Interactive content in the center (Camera for AI steps, List for Selection steps).
   - Confirmation at the bottom.
3. **Completion:** Clear visual confirmation with `TicketAnimation` for a satisfying end-to-end experience.

---

## 💡 Design Goal for Stitch
- **Consistency:** Ensure all "AI Recognition" pages feel identical in layout.
- **Modernization:** Enhance the "Kiosk" feel with better shadows, micro-interactions, and refined typography.
- **Accessibility:** Ensure high contrast for all text elements and clear visual cues for recognition status.
