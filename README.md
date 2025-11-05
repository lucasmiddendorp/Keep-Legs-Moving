# 🚴‍♂️ Keep Legs Moving (KLM)

**Keep Legs Moving (KLM)** is a Python-based cycling training planner that helps you create, adapt, and analyze structured workouts — just like JOIN Cycling, but open, customizable, and fun.  
It combines basic training load modeling, adaptive workout planning, and performance tracking to help you keep your legs moving smartly.

---

## ✨ Features

- 🧠 **Adaptive Workout Planning** — generates a weekly plan based on your fitness and availability.  
- 📈 **Training Load Modeling** — tracks fitness, fatigue, and readiness (CTL–ATL model).  
- ⚡ **Smart Intensity Selection** — adjusts workouts based on a smart ML model.  
- 💾 **Workout Library** — predefined sessions for recovery, endurance, threshold, and VO₂max.  
- 📊 **Metrics Calculation** — TSS, IF, NP from power data.  
- 🧩 **Modular Design** — easily extendable to integrate with Strava or export `.zwo` files.

---

## 🏗️ Project Structure

Core/
-- adaptation_engine: Dynamically adapts upcoming workouts based on fatigue, missed sessions, or readiness score.
-- performance_model: Predicts changes in FTP or performance over time using fitness and fatigue trends.
-- training_load_model: Implements fitness-fatigue (CTL–ATL) model to estimate training readiness.
-- workout_planner: Builds personalized weekly workout plans based on user profile and availability.

Data/
-- activity_loader: Loads past ride data (e.g., from Strava, FIT/TCX/GPX files) and converts it into metrics.
-- power_metrics: Calculates key cycling metrics like NP, IF, TSS, average power, and energy expenditure.

storage/
-- database: Handles saving and loading of user data, workouts, and performance history (SQLite or JSON).

ui/
-- dashboard: Simple Streamlit, CTI or PowerBI dashboard to visualize training progress and upcoming sessions.

main.py: Entry point to run KLM: initializes models, loads user data, generates plan, and displays results.