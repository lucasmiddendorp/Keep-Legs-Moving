from dataclasses import dataclass
import streamlit as st
import config
import pandas as pd


@dataclass
class PacingSettings:
    rider_weight: float
    bike_weight: float
    gear_weight: float

    ftp: int
    target_if: float
    max_ftp_fraction: float
    min_ftp_fraction: float
    pacing_aggression: float

    reference_speed_kmh: float
    max_speed_kmh: float

    cda_normal: float
    cda_aero: float
    crr: float
    drivetrain_efficiency: float
    air_density: float

    coast_grade_threshold: float
    coast_speed_cap: float
    aero_pos_speed: float

    wind_speed: float
    wind_from_deg: float

    @property
    def total_mass(self):
        return self.rider_weight + self.bike_weight + self.gear_weight

    @classmethod
    def from_sidebar(cls):

        st.sidebar.header("Rider And Bike")

        rider_weight = st.sidebar.number_input("Rider weight (kg)", min_value=30.0, max_value=130.0, value=75.0, step=0.5)
        bike_weight = st.sidebar.number_input("Bike weight (kg)", min_value=4.0, max_value=25.0, value=8.0, step=0.5)
        gear_weight = st.sidebar.number_input("Bottles and gear (kg)", min_value=0.0, max_value=20.0, value=2.0, step=0.5)

        st.sidebar.header("NP Pacing Target")
        pacing_ftp = st.sidebar.number_input("FTP (W)", min_value=100, max_value=600, value=int(config.FTP), step=5)
        target_if_percent = st.sidebar.number_input("Target IF (% FTP)", min_value=40, max_value=120, value=82, step=1)
        max_ftp_percent = st.sidebar.number_input("Max short effort (% FTP)", min_value=target_if_percent, max_value=180, value=115, step=1)
        min_ftp_percent = st.sidebar.number_input("Minimum pedaling (% FTP)", min_value=0, max_value=target_if_percent, value=0, step=1)
        pacing_aggression = st.sidebar.slider("Pacing variability", min_value=0.0, max_value=1.0, value=0.45, step=0.05)
        min_section_km = st.sidebar.number_input("Minimum section length (km)", min_value=0.2, max_value=10.0, value=1.0, step=0.1)
        max_speed_kmh = st.sidebar.number_input("Max descending speed (km/h)", min_value=20.0, max_value=120.0, value=75.0, step=1.0)
        coast_grade_threshold = st.sidebar.number_input("Coasting grade threshold", min_value=0.02, max_value=0.2, value=0.05, step=0.005)
        coast_speed_cap = st.sidebar.number_input("Coasting speed cap (km/h)", min_value=0.0, max_value=120.0, value=45.0, step=1.0)
        aero_pos_speed = st.sidebar.number_input("Aero position speed (km/h)", min_value=20.0, max_value=60.0, value=40.0, step=1.0)

        st.sidebar.header("Model Assumptions")
        cda_normal = st.sidebar.number_input("CdA (m2)", min_value=0.15, max_value=0.70, value=0.32, step=0.01)
        cda_aero = st.sidebar.number_input("CdA Aero (m2)", min_value=0.15, max_value=0.50, value=0.25, step=0.01)
        crr = st.sidebar.number_input("Rolling resistance Crr", min_value=0.0010, max_value=0.0200, value=0.0045, step=0.0005, format="%.4f")
        drivetrain_efficiency = st.sidebar.number_input("Drivetrain efficiency", min_value=0.85, max_value=1.00, value=0.975, step=0.005)
        air_density = st.sidebar.number_input("Air density (kg/m3)", min_value=0.90, max_value=1.35, value=1.18, step=0.01)
        wind_speed_kmh = st.sidebar.number_input("Wind speed (km/h)", min_value=0.0, max_value=80.0, value=0.0, step=1.0)
        wind_from_deg = st.sidebar.number_input("Wind from direction (degrees)", min_value=0, max_value=359, value=0, step=5)

        return cls(
            rider_weight=rider_weight,
            bike_weight=bike_weight,
            gear_weight=gear_weight,
            ftp=pacing_ftp,
            target_if=target_if_percent / 100,
            max_ftp_fraction=max_ftp_percent / 100,
            min_ftp_fraction=min_ftp_percent / 100,
            pacing_aggression=pacing_aggression,
            reference_speed_kmh=35,
            max_speed_kmh=max_speed_kmh,
            cda_normal=cda_normal,
            cda_aero=cda_aero,
            crr=crr,
            drivetrain_efficiency=drivetrain_efficiency,
            air_density=air_density,
            wind_speed=wind_speed_kmh / 3.6,
            wind_from_deg=wind_from_deg,
            coast_grade_threshold=coast_grade_threshold,
            coast_speed_cap=coast_speed_cap,
            aero_pos_speed=aero_pos_speed,
        )
    
    def assumptions_dataframe(self):

        wind_speed_kmh = self.wind_speed * 3.6

        return pd.DataFrame(
            [
                (
                    "Total system mass",
                    f"{self.total_mass:.1f} kg"
                ),
                (
                    "Rolling resistance",
                    f"Crr {self.crr:.4f}"
                ),
                (
                    "Aerodynamics Normal",
                    f"CdA {self.cda_normal:.2f} m²"
                ),
                (
                    "Aerodynamics (Aero)",
                    f"CdA {self.cda_aero:.2f} m²"
                ),
                (
                    "Drivetrain efficiency",
                    f"{self.drivetrain_efficiency * 100:.1f}%"
                ),
                (
                    "Air density",
                    f"{self.air_density:.2f} kg/m³"
                ),
                (
                    "Wind vector",
                    f"{wind_speed_kmh:.1f} km/h from {self.wind_from_deg:.0f}°"
                ),
                (
                    "FTP",
                    f"{self.ftp:.0f} W"
                ),
                (
                    "Target Normalized Power",
                    f"{self.ftp * self.target_if:.0f} W ({self.target_if * 100:.0f}% FTP)"
                ),
                (
                    "Short-effort cap",
                    f"{self.ftp * self.max_ftp_fraction:.0f} W ({self.max_ftp_fraction * 100:.0f}% FTP)"
                ),
                (
                    "Minimum pedaling floor",
                    f"{self.ftp * self.min_ftp_fraction:.0f} W ({self.min_ftp_fraction * 100:.0f}% FTP)"
                ),
                (
                    "Pacing variability",
                    f"{self.pacing_aggression:.2f}"
                ),
                (
                    "Speed cap",
                    f"{self.max_speed_kmh:.1f} km/h"
                ),
                (
                    "Aero position speed",
                    f"{self.aero_pos_speed:.1f} km/h"
                ),
            ],
            columns=["Assumption", "Value"]
        )