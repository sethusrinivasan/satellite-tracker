"""Daily temperature trends for cities over 1 million people (Open-Meteo ERA5)."""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.services import overlay_http
from app.services.overlay_cache import (
    PENDING_TTL_SECONDS,
    get_fresh,
    get_stale,
    store,
)

log = logging.getLogger(__name__)

OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_HOME = "https://open-meteo.com/"
REQUEST_TIMEOUT = 25
BATCH_SIZE = 40
HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/json",
}

SOURCE = {
    "name": "Open-Meteo",
    "url": OPEN_METEO_HOME,
    "license": "CC BY 4.0; no API key",
    "attribution": (
        "City temperature trends from Open-Meteo daily 2 m means (ERA5 / Copernicus). "
        "Pins are urban areas with population over 1 million. "
        "7d / 30d / 90d / 1y values are °C change versus that lookback."
    ),
}

PERIODS = (("7d", 7), ("30d", 30), ("90d", 90), ("1y", 365))

# Urban areas with population over 1 million. pop_m is an approximate UN/census figure.
MILLION_CITIES: list[dict[str, Any]] = [
    {"name": "Tokyo", "country": "Japan", "lat": 35.6762, "lng": 139.6503, "pop_m": 37.4},
    {"name": "Delhi", "country": "India", "lat": 28.6139, "lng": 77.2090, "pop_m": 32.9},
    {"name": "Shanghai", "country": "China", "lat": 31.2304, "lng": 121.4737, "pop_m": 29.2},
    {"name": "Dhaka", "country": "Bangladesh", "lat": 23.8103, "lng": 90.4125, "pop_m": 23.2},
    {"name": "São Paulo", "country": "Brazil", "lat": -23.5558, "lng": -46.6396, "pop_m": 22.6},
    {"name": "Cairo", "country": "Egypt", "lat": 30.0444, "lng": 31.2357, "pop_m": 22.2},
    {"name": "Mexico City", "country": "Mexico", "lat": 19.4326, "lng": -99.1332, "pop_m": 22.1},
    {"name": "Beijing", "country": "China", "lat": 39.9042, "lng": 116.4074, "pop_m": 21.8},
    {"name": "Mumbai", "country": "India", "lat": 19.0760, "lng": 72.8777, "pop_m": 21.3},
    {"name": "Osaka", "country": "Japan", "lat": 34.6937, "lng": 135.5023, "pop_m": 19.1},
    {"name": "Chongqing", "country": "China", "lat": 29.5630, "lng": 106.5516, "pop_m": 17.3},
    {"name": "Karachi", "country": "Pakistan", "lat": 24.8607, "lng": 67.0011, "pop_m": 17.2},
    {"name": "Istanbul", "country": "Türkiye", "lat": 41.0082, "lng": 28.9784, "pop_m": 16.0},
    {"name": "Kinshasa", "country": "DR Congo", "lat": -4.4419, "lng": 15.2663, "pop_m": 15.6},
    {"name": "Lagos", "country": "Nigeria", "lat": 6.5244, "lng": 3.3792, "pop_m": 15.4},
    {"name": "Buenos Aires", "country": "Argentina", "lat": -34.6037, "lng": -58.3816, "pop_m": 15.4},
    {"name": "Kolkata", "country": "India", "lat": 22.5726, "lng": 88.3639, "pop_m": 15.1},
    {"name": "Manila", "country": "Philippines", "lat": 14.5995, "lng": 120.9842, "pop_m": 14.4},
    {"name": "Tianjin", "country": "China", "lat": 39.3434, "lng": 117.3616, "pop_m": 14.0},
    {"name": "Guangzhou", "country": "China", "lat": 23.1291, "lng": 113.2644, "pop_m": 13.9},
    {"name": "Rio de Janeiro", "country": "Brazil", "lat": -22.9068, "lng": -43.1729, "pop_m": 13.6},
    {"name": "Lahore", "country": "Pakistan", "lat": 31.5204, "lng": 74.3587, "pop_m": 13.5},
    {"name": "Bangalore", "country": "India", "lat": 12.9716, "lng": 77.5946, "pop_m": 13.2},
    {"name": "Shenzhen", "country": "China", "lat": 22.5431, "lng": 114.0579, "pop_m": 13.0},
    {"name": "Moscow", "country": "Russia", "lat": 55.7558, "lng": 37.6173, "pop_m": 12.7},
    {"name": "Chennai", "country": "India", "lat": 13.0827, "lng": 80.2707, "pop_m": 11.6},
    {"name": "Bogotá", "country": "Colombia", "lat": 4.7110, "lng": -74.0721, "pop_m": 11.3},
    {"name": "Paris", "country": "France", "lat": 48.8566, "lng": 2.3522, "pop_m": 11.1},
    {"name": "Jakarta", "country": "Indonesia", "lat": -6.2088, "lng": 106.8456, "pop_m": 11.1},
    {"name": "Lima", "country": "Peru", "lat": -12.0464, "lng": -77.0428, "pop_m": 11.0},
    {"name": "Bangkok", "country": "Thailand", "lat": 13.7563, "lng": 100.5018, "pop_m": 10.9},
    {"name": "Hyderabad", "country": "India", "lat": 17.3850, "lng": 78.4867, "pop_m": 10.5},
    {"name": "Seoul", "country": "South Korea", "lat": 37.5665, "lng": 126.9780, "pop_m": 10.0},
    {"name": "Nagoya", "country": "Japan", "lat": 35.1815, "lng": 136.9066, "pop_m": 9.6},
    {"name": "London", "country": "United Kingdom", "lat": 51.5074, "lng": -0.1278, "pop_m": 9.6},
    {"name": "Chengdu", "country": "China", "lat": 30.5728, "lng": 104.0668, "pop_m": 9.5},
    {"name": "Nanjing", "country": "China", "lat": 32.0603, "lng": 118.7969, "pop_m": 9.3},
    {"name": "Tehran", "country": "Iran", "lat": 35.6892, "lng": 51.3890, "pop_m": 9.3},
    {"name": "Ho Chi Minh City", "country": "Vietnam", "lat": 10.8231, "lng": 106.6297, "pop_m": 9.3},
    {"name": "Luanda", "country": "Angola", "lat": -8.8390, "lng": 13.2894, "pop_m": 9.0},
    {"name": "Ahmedabad", "country": "India", "lat": 23.0225, "lng": 72.5714, "pop_m": 8.6},
    {"name": "Kuala Lumpur", "country": "Malaysia", "lat": 3.1390, "lng": 101.6869, "pop_m": 8.6},
    {"name": "Xi'an", "country": "China", "lat": 34.3416, "lng": 108.9398, "pop_m": 8.5},
    {"name": "Hong Kong", "country": "China", "lat": 22.3193, "lng": 114.1694, "pop_m": 7.5},
    {"name": "Dongguan", "country": "China", "lat": 23.0207, "lng": 113.7518, "pop_m": 7.5},
    {"name": "Hangzhou", "country": "China", "lat": 30.2741, "lng": 120.1551, "pop_m": 7.5},
    {"name": "Foshan", "country": "China", "lat": 23.0215, "lng": 113.1214, "pop_m": 7.4},
    {"name": "Riyadh", "country": "Saudi Arabia", "lat": 24.7136, "lng": 46.6753, "pop_m": 7.4},
    {"name": "Shenyang", "country": "China", "lat": 41.8057, "lng": 123.4315, "pop_m": 7.3},
    {"name": "Baghdad", "country": "Iraq", "lat": 33.3152, "lng": 44.3661, "pop_m": 7.2},
    {"name": "Santiago", "country": "Chile", "lat": -33.4489, "lng": -70.6693, "pop_m": 6.9},
    {"name": "Surat", "country": "India", "lat": 21.1702, "lng": 72.8311, "pop_m": 6.8},
    {"name": "Madrid", "country": "Spain", "lat": 40.4168, "lng": -3.7038, "pop_m": 6.7},
    {"name": "Suzhou", "country": "China", "lat": 31.2989, "lng": 120.5853, "pop_m": 6.7},
    {"name": "Pune", "country": "India", "lat": 18.5204, "lng": 73.8567, "pop_m": 6.6},
    {"name": "Harbin", "country": "China", "lat": 45.8038, "lng": 126.5340, "pop_m": 6.4},
    {"name": "Houston", "country": "United States", "lat": 29.7604, "lng": -95.3698, "pop_m": 6.4},
    {"name": "Dallas", "country": "United States", "lat": 32.7767, "lng": -96.7970, "pop_m": 6.4},
    {"name": "Toronto", "country": "Canada", "lat": 43.6532, "lng": -79.3832, "pop_m": 6.3},
    {"name": "Dar es Salaam", "country": "Tanzania", "lat": -6.7924, "lng": 39.2083, "pop_m": 6.3},
    {"name": "Miami", "country": "United States", "lat": 25.7617, "lng": -80.1918, "pop_m": 6.2},
    {"name": "Belo Horizonte", "country": "Brazil", "lat": -19.9167, "lng": -43.9345, "pop_m": 6.1},
    {"name": "Singapore", "country": "Singapore", "lat": 1.3521, "lng": 103.8198, "pop_m": 6.0},
    {"name": "Philadelphia", "country": "United States", "lat": 39.9526, "lng": -75.1652, "pop_m": 5.8},
    {"name": "Atlanta", "country": "United States", "lat": 33.7490, "lng": -84.3880, "pop_m": 5.7},
    {"name": "Khartoum", "country": "Sudan", "lat": 15.5007, "lng": 32.5599, "pop_m": 5.7},
    {"name": "Barcelona", "country": "Spain", "lat": 41.3874, "lng": 2.1686, "pop_m": 5.6},
    {"name": "Johannesburg", "country": "South Africa", "lat": -26.2041, "lng": 28.0473, "pop_m": 5.6},
    {"name": "Saint Petersburg", "country": "Russia", "lat": 59.9311, "lng": 30.3609, "pop_m": 5.5},
    {"name": "Qingdao", "country": "China", "lat": 36.0671, "lng": 120.3826, "pop_m": 5.5},
    {"name": "Dalian", "country": "China", "lat": 38.9140, "lng": 121.6147, "pop_m": 5.5},
    {"name": "Washington", "country": "United States", "lat": 38.9072, "lng": -77.0369, "pop_m": 5.4},
    {"name": "Yangon", "country": "Myanmar", "lat": 16.8409, "lng": 96.1735, "pop_m": 5.4},
    {"name": "Alexandria", "country": "Egypt", "lat": 31.2001, "lng": 29.9187, "pop_m": 5.4},
    {"name": "Jinan", "country": "China", "lat": 36.6512, "lng": 117.1201, "pop_m": 5.3},
    {"name": "Guadalajara", "country": "Mexico", "lat": 20.6597, "lng": -103.3496, "pop_m": 5.3},
    {"name": "Ankara", "country": "Türkiye", "lat": 39.9334, "lng": 32.8597, "pop_m": 5.2},
    {"name": "Melbourne", "country": "Australia", "lat": -37.8136, "lng": 144.9631, "pop_m": 5.2},
    {"name": "Sydney", "country": "Australia", "lat": -33.8688, "lng": 151.2093, "pop_m": 5.2},
    {"name": "Monterrey", "country": "Mexico", "lat": 25.6866, "lng": -100.3161, "pop_m": 5.1},
    {"name": "Changsha", "country": "China", "lat": 28.2282, "lng": 112.9388, "pop_m": 5.0},
    {"name": "Cape Town", "country": "South Africa", "lat": -33.9249, "lng": 18.4241, "pop_m": 4.8},
    {"name": "Brasilia", "country": "Brazil", "lat": -15.7975, "lng": -47.8919, "pop_m": 4.7},
    {"name": "New York", "country": "United States", "lat": 40.7128, "lng": -74.0060, "pop_m": 18.8},
    {"name": "Los Angeles", "country": "United States", "lat": 34.0522, "lng": -118.2437, "pop_m": 12.5},
    {"name": "Chicago", "country": "United States", "lat": 41.8781, "lng": -87.6298, "pop_m": 8.9},
    {"name": "Phoenix", "country": "United States", "lat": 33.4484, "lng": -112.0740, "pop_m": 4.9},
    {"name": "San Francisco", "country": "United States", "lat": 37.7749, "lng": -122.4194, "pop_m": 4.6},
    {"name": "Boston", "country": "United States", "lat": 42.3601, "lng": -71.0589, "pop_m": 4.4},
    {"name": "Detroit", "country": "United States", "lat": 42.3314, "lng": -83.0458, "pop_m": 3.5},
    {"name": "Seattle", "country": "United States", "lat": 47.6062, "lng": -122.3321, "pop_m": 3.5},
    {"name": "Minneapolis", "country": "United States", "lat": 44.9778, "lng": -93.2650, "pop_m": 2.9},
    {"name": "Denver", "country": "United States", "lat": 39.7392, "lng": -104.9903, "pop_m": 2.9},
    {"name": "Berlin", "country": "Germany", "lat": 52.5200, "lng": 13.4050, "pop_m": 3.6},
    {"name": "Rome", "country": "Italy", "lat": 41.9028, "lng": 12.4964, "pop_m": 2.9},
    {"name": "Milan", "country": "Italy", "lat": 45.4642, "lng": 9.1900, "pop_m": 3.1},
    {"name": "Naples", "country": "Italy", "lat": 40.8518, "lng": 14.2681, "pop_m": 3.1},
    {"name": "Athens", "country": "Greece", "lat": 37.9838, "lng": 23.7275, "pop_m": 3.2},
    {"name": "Lisbon", "country": "Portugal", "lat": 38.7223, "lng": -9.1393, "pop_m": 3.0},
    {"name": "Vienna", "country": "Austria", "lat": 48.2082, "lng": 16.3738, "pop_m": 2.0},
    {"name": "Budapest", "country": "Hungary", "lat": 47.4979, "lng": 19.0402, "pop_m": 1.8},
    {"name": "Warsaw", "country": "Poland", "lat": 52.2297, "lng": 21.0122, "pop_m": 1.8},
    {"name": "Prague", "country": "Czechia", "lat": 50.0755, "lng": 14.4378, "pop_m": 1.3},
    {"name": "Bucharest", "country": "Romania", "lat": 44.4268, "lng": 26.1025, "pop_m": 1.8},
    {"name": "Munich", "country": "Germany", "lat": 48.1351, "lng": 11.5820, "pop_m": 1.6},
    {"name": "Hamburg", "country": "Germany", "lat": 53.5511, "lng": 9.9937, "pop_m": 1.8},
    {"name": "Brussels", "country": "Belgium", "lat": 50.8503, "lng": 4.3517, "pop_m": 2.1},
    {"name": "Amsterdam", "country": "Netherlands", "lat": 52.3676, "lng": 4.9041, "pop_m": 1.2},
    {"name": "Stockholm", "country": "Sweden", "lat": 59.3293, "lng": 18.0686, "pop_m": 1.7},
    {"name": "Copenhagen", "country": "Denmark", "lat": 55.6761, "lng": 12.5683, "pop_m": 1.4},
    {"name": "Helsinki", "country": "Finland", "lat": 60.1699, "lng": 24.9384, "pop_m": 1.3},
    {"name": "Oslo", "country": "Norway", "lat": 59.9139, "lng": 10.7522, "pop_m": 1.1},
    {"name": "Dublin", "country": "Ireland", "lat": 53.3498, "lng": -6.2603, "pop_m": 1.3},
    {"name": "Zurich", "country": "Switzerland", "lat": 47.3769, "lng": 8.5417, "pop_m": 1.4},
    {"name": "Kyiv", "country": "Ukraine", "lat": 50.4501, "lng": 30.5234, "pop_m": 3.0},
    {"name": "Minsk", "country": "Belarus", "lat": 53.9006, "lng": 27.5590, "pop_m": 2.0},
    {"name": "Tashkent", "country": "Uzbekistan", "lat": 41.2995, "lng": 69.2401, "pop_m": 2.6},
    {"name": "Almaty", "country": "Kazakhstan", "lat": 43.2220, "lng": 76.8512, "pop_m": 2.2},
    {"name": "Baku", "country": "Azerbaijan", "lat": 40.4093, "lng": 49.8671, "pop_m": 2.3},
    {"name": "Tbilisi", "country": "Georgia", "lat": 41.7151, "lng": 44.8271, "pop_m": 1.2},
    {"name": "Yerevan", "country": "Armenia", "lat": 40.1872, "lng": 44.5152, "pop_m": 1.1},
    {"name": "Tel Aviv", "country": "Israel", "lat": 32.0853, "lng": 34.7818, "pop_m": 4.2},
    {"name": "Amman", "country": "Jordan", "lat": 31.9454, "lng": 35.9284, "pop_m": 2.2},
    {"name": "Beirut", "country": "Lebanon", "lat": 33.8938, "lng": 35.5018, "pop_m": 2.2},
    {"name": "Damascus", "country": "Syria", "lat": 33.5138, "lng": 36.2765, "pop_m": 2.5},
    {"name": "Jeddah", "country": "Saudi Arabia", "lat": 21.4858, "lng": 39.1925, "pop_m": 4.7},
    {"name": "Mecca", "country": "Saudi Arabia", "lat": 21.3891, "lng": 39.8579, "pop_m": 2.1},
    {"name": "Doha", "country": "Qatar", "lat": 25.2854, "lng": 51.5310, "pop_m": 2.4},
    {"name": "Dubai", "country": "United Arab Emirates", "lat": 25.2048, "lng": 55.2708, "pop_m": 3.6},
    {"name": "Abu Dhabi", "country": "United Arab Emirates", "lat": 24.4539, "lng": 54.3773, "pop_m": 1.5},
    {"name": "Kuwait City", "country": "Kuwait", "lat": 29.3759, "lng": 47.9774, "pop_m": 3.1},
    {"name": "Sana'a", "country": "Yemen", "lat": 15.3694, "lng": 44.1910, "pop_m": 3.0},
    {"name": "Muscat", "country": "Oman", "lat": 23.5880, "lng": 58.3829, "pop_m": 1.6},
    {"name": "Casablanca", "country": "Morocco", "lat": 33.5731, "lng": -7.5898, "pop_m": 3.8},
    {"name": "Algiers", "country": "Algeria", "lat": 36.7538, "lng": 3.0588, "pop_m": 2.8},
    {"name": "Tunis", "country": "Tunisia", "lat": 36.8065, "lng": 10.1815, "pop_m": 2.7},
    {"name": "Tripoli", "country": "Libya", "lat": 32.8872, "lng": 13.1913, "pop_m": 1.2},
    {"name": "Addis Ababa", "country": "Ethiopia", "lat": 9.0320, "lng": 38.7469, "pop_m": 5.2},
    {"name": "Nairobi", "country": "Kenya", "lat": -1.2921, "lng": 36.8219, "pop_m": 5.1},
    {"name": "Kampala", "country": "Uganda", "lat": 0.3476, "lng": 32.5825, "pop_m": 3.6},
    {"name": "Kigali", "country": "Rwanda", "lat": -1.9441, "lng": 30.0619, "pop_m": 1.2},
    {"name": "Accra", "country": "Ghana", "lat": 5.6037, "lng": -0.1870, "pop_m": 2.6},
    {"name": "Abidjan", "country": "Côte d'Ivoire", "lat": 5.3600, "lng": -4.0083, "pop_m": 5.4},
    {"name": "Dakar", "country": "Senegal", "lat": 14.7167, "lng": -17.4677, "pop_m": 3.3},
    {"name": "Bamako", "country": "Mali", "lat": 12.6392, "lng": -8.0029, "pop_m": 2.8},
    {"name": "Ouagadougou", "country": "Burkina Faso", "lat": 12.3714, "lng": -1.5197, "pop_m": 2.7},
    {"name": "Conakry", "country": "Guinea", "lat": 9.6412, "lng": -13.5784, "pop_m": 2.0},
    {"name": "Ibadan", "country": "Nigeria", "lat": 7.3775, "lng": 3.9470, "pop_m": 3.8},
    {"name": "Kano", "country": "Nigeria", "lat": 12.0022, "lng": 8.5920, "pop_m": 4.2},
    {"name": "Abuja", "country": "Nigeria", "lat": 9.0765, "lng": 7.3986, "pop_m": 3.6},
    {"name": "Yaoundé", "country": "Cameroon", "lat": 3.8480, "lng": 11.5021, "pop_m": 4.1},
    {"name": "Douala", "country": "Cameroon", "lat": 4.0511, "lng": 9.7679, "pop_m": 3.9},
    {"name": "Lusaka", "country": "Zambia", "lat": -15.3875, "lng": 28.3228, "pop_m": 2.7},
    {"name": "Harare", "country": "Zimbabwe", "lat": -17.8252, "lng": 31.0335, "pop_m": 1.5},
    {"name": "Maputo", "country": "Mozambique", "lat": -25.9692, "lng": 32.5732, "pop_m": 1.1},
    {"name": "Antananarivo", "country": "Madagascar", "lat": -18.8792, "lng": 47.5079, "pop_m": 3.4},
    {"name": "Durban", "country": "South Africa", "lat": -29.8587, "lng": 31.0218, "pop_m": 3.1},
    {"name": "Pretoria", "country": "South Africa", "lat": -25.7479, "lng": 28.2293, "pop_m": 2.7},
    {"name": "Jaipur", "country": "India", "lat": 26.9124, "lng": 75.7873, "pop_m": 4.1},
    {"name": "Lucknow", "country": "India", "lat": 26.8467, "lng": 80.9462, "pop_m": 3.6},
    {"name": "Kanpur", "country": "India", "lat": 26.4499, "lng": 80.3319, "pop_m": 3.1},
    {"name": "Nagpur", "country": "India", "lat": 21.1458, "lng": 79.0882, "pop_m": 2.9},
    {"name": "Indore", "country": "India", "lat": 22.7196, "lng": 75.8577, "pop_m": 2.6},
    {"name": "Bhopal", "country": "India", "lat": 23.2599, "lng": 77.4126, "pop_m": 2.4},
    {"name": "Patna", "country": "India", "lat": 25.5941, "lng": 85.1376, "pop_m": 2.5},
    {"name": "Vadodara", "country": "India", "lat": 22.3072, "lng": 73.1812, "pop_m": 2.2},
    {"name": "Coimbatore", "country": "India", "lat": 11.0168, "lng": 76.9558, "pop_m": 2.5},
    {"name": "Kochi", "country": "India", "lat": 9.9312, "lng": 76.2673, "pop_m": 2.1},
    {"name": "Visakhapatnam", "country": "India", "lat": 17.6868, "lng": 83.2185, "pop_m": 2.0},
    {"name": "Thiruvananthapuram", "country": "India", "lat": 8.5241, "lng": 76.9366, "pop_m": 1.7},
    {"name": "Kathmandu", "country": "Nepal", "lat": 27.7172, "lng": 85.3240, "pop_m": 1.4},
    {"name": "Colombo", "country": "Sri Lanka", "lat": 6.9271, "lng": 79.8612, "pop_m": 2.3},
    {"name": "Chittagong", "country": "Bangladesh", "lat": 22.3569, "lng": 91.7832, "pop_m": 5.3},
    {"name": "Islamabad", "country": "Pakistan", "lat": 33.6844, "lng": 73.0479, "pop_m": 1.2},
    {"name": "Faisalabad", "country": "Pakistan", "lat": 31.4504, "lng": 73.1350, "pop_m": 3.7},
    {"name": "Rawalpindi", "country": "Pakistan", "lat": 33.5651, "lng": 73.0169, "pop_m": 2.3},
    {"name": "Kabul", "country": "Afghanistan", "lat": 34.5553, "lng": 69.2075, "pop_m": 4.6},
    {"name": "Tashkent", "country": "Uzbekistan", "lat": 41.2995, "lng": 69.2401, "pop_m": 2.6},
    {"name": "Wuhan", "country": "China", "lat": 30.5928, "lng": 114.3055, "pop_m": 8.3},
    {"name": "Zhengzhou", "country": "China", "lat": 34.7466, "lng": 113.6254, "pop_m": 6.5},
    {"name": "Kunming", "country": "China", "lat": 25.0389, "lng": 102.7183, "pop_m": 4.4},
    {"name": "Taiyuan", "country": "China", "lat": 37.8706, "lng": 112.5489, "pop_m": 4.3},
    {"name": "Hefei", "country": "China", "lat": 31.8206, "lng": 117.2272, "pop_m": 4.2},
    {"name": "Ürümqi", "country": "China", "lat": 43.8256, "lng": 87.6168, "pop_m": 4.1},
    {"name": "Nanning", "country": "China", "lat": 22.8170, "lng": 108.3665, "pop_m": 3.8},
    {"name": "Lanzhou", "country": "China", "lat": 36.0611, "lng": 103.8343, "pop_m": 3.6},
    {"name": "Taipei", "country": "Taiwan", "lat": 25.0330, "lng": 121.5654, "pop_m": 2.7},
    {"name": "Kaohsiung", "country": "Taiwan", "lat": 22.6273, "lng": 120.3014, "pop_m": 2.7},
    {"name": "Pyongyang", "country": "North Korea", "lat": 39.0392, "lng": 125.7625, "pop_m": 3.0},
    {"name": "Busan", "country": "South Korea", "lat": 35.1796, "lng": 129.0756, "pop_m": 3.4},
    {"name": "Incheon", "country": "South Korea", "lat": 37.4563, "lng": 126.7052, "pop_m": 2.9},
    {"name": "Hanoi", "country": "Vietnam", "lat": 21.0278, "lng": 105.8342, "pop_m": 5.2},
    {"name": "Haiphong", "country": "Vietnam", "lat": 20.8449, "lng": 106.6881, "pop_m": 2.1},
    {"name": "Phnom Penh", "country": "Cambodia", "lat": 11.5564, "lng": 104.9282, "pop_m": 2.3},
    {"name": "Vientiane", "country": "Laos", "lat": 17.9757, "lng": 102.6331, "pop_m": 1.0},
    {"name": "Bangkok", "country": "Thailand", "lat": 13.7563, "lng": 100.5018, "pop_m": 10.9},
    {"name": "Yangon", "country": "Myanmar", "lat": 16.8409, "lng": 96.1735, "pop_m": 5.4},
    {"name": "Mandalay", "country": "Myanmar", "lat": 21.9588, "lng": 96.0891, "pop_m": 1.5},
    {"name": "Jakarta", "country": "Indonesia", "lat": -6.2088, "lng": 106.8456, "pop_m": 11.1},
    {"name": "Surabaya", "country": "Indonesia", "lat": -7.2575, "lng": 112.7521, "pop_m": 3.0},
    {"name": "Bandung", "country": "Indonesia", "lat": -6.9175, "lng": 107.6191, "pop_m": 2.5},
    {"name": "Medan", "country": "Indonesia", "lat": 3.5952, "lng": 98.6722, "pop_m": 2.4},
    {"name": "Makassar", "country": "Indonesia", "lat": -5.1477, "lng": 119.4327, "pop_m": 1.5},
    {"name": "Quezon City", "country": "Philippines", "lat": 14.6760, "lng": 121.0437, "pop_m": 3.0},
    {"name": "Cebu", "country": "Philippines", "lat": 10.3157, "lng": 123.8854, "pop_m": 1.0},
    {"name": "Ulaanbaatar", "country": "Mongolia", "lat": 47.8864, "lng": 106.9057, "pop_m": 1.6},
    {"name": "Perth", "country": "Australia", "lat": -31.9505, "lng": 115.8605, "pop_m": 2.2},
    {"name": "Brisbane", "country": "Australia", "lat": -27.4705, "lng": 153.0260, "pop_m": 2.6},
    {"name": "Auckland", "country": "New Zealand", "lat": -36.8509, "lng": 174.7645, "pop_m": 1.7},
    {"name": "Auckland", "country": "New Zealand", "lat": -36.8509, "lng": 174.7645, "pop_m": 1.7},
    {"name": "Vancouver", "country": "Canada", "lat": 49.2827, "lng": -123.1207, "pop_m": 2.6},
    {"name": "Montreal", "country": "Canada", "lat": 45.5017, "lng": -73.5673, "pop_m": 4.3},
    {"name": "Calgary", "country": "Canada", "lat": 51.0447, "lng": -114.0719, "pop_m": 1.5},
    {"name": "Edmonton", "country": "Canada", "lat": 53.5461, "lng": -113.4938, "pop_m": 1.5},
    {"name": "Ottawa", "country": "Canada", "lat": 45.4215, "lng": -75.6972, "pop_m": 1.5},
    {"name": "Guatemala City", "country": "Guatemala", "lat": 14.6349, "lng": -90.5069, "pop_m": 3.0},
    {"name": "San Salvador", "country": "El Salvador", "lat": 13.6929, "lng": -89.2182, "pop_m": 1.1},
    {"name": "Tegucigalpa", "country": "Honduras", "lat": 14.0723, "lng": -87.1921, "pop_m": 1.4},
    {"name": "Managua", "country": "Nicaragua", "lat": 12.1150, "lng": -86.2362, "pop_m": 1.1},
    {"name": "San José", "country": "Costa Rica", "lat": 9.9281, "lng": -84.0907, "pop_m": 1.4},
    {"name": "Panama City", "country": "Panama", "lat": 8.9824, "lng": -79.5199, "pop_m": 1.9},
    {"name": "Havana", "country": "Cuba", "lat": 23.1136, "lng": -82.3666, "pop_m": 2.1},
    {"name": "Santo Domingo", "country": "Dominican Republic", "lat": 18.4861, "lng": -69.9312, "pop_m": 3.3},
    {"name": "San Juan", "country": "Puerto Rico", "lat": 18.4655, "lng": -66.1057, "pop_m": 2.4},
    {"name": "Caracas", "country": "Venezuela", "lat": 10.4806, "lng": -66.9036, "pop_m": 2.9},
    {"name": "Maracaibo", "country": "Venezuela", "lat": 10.6427, "lng": -71.6125, "pop_m": 2.7},
    {"name": "Medellín", "country": "Colombia", "lat": 6.2476, "lng": -75.5658, "pop_m": 4.0},
    {"name": "Cali", "country": "Colombia", "lat": 3.4516, "lng": -76.5320, "pop_m": 2.8},
    {"name": "Quito", "country": "Ecuador", "lat": -0.1807, "lng": -78.4678, "pop_m": 2.0},
    {"name": "Guayaquil", "country": "Ecuador", "lat": -2.1894, "lng": -79.8891, "pop_m": 3.1},
    {"name": "La Paz", "country": "Bolivia", "lat": -16.4897, "lng": -68.1193, "pop_m": 1.9},
    {"name": "Santa Cruz", "country": "Bolivia", "lat": -17.8146, "lng": -63.1561, "pop_m": 1.8},
    {"name": "Asunción", "country": "Paraguay", "lat": -25.2637, "lng": -57.5759, "pop_m": 3.3},
    {"name": "Montevideo", "country": "Uruguay", "lat": -34.9011, "lng": -56.1645, "pop_m": 1.8},
    {"name": "Recife", "country": "Brazil", "lat": -8.0476, "lng": -34.8770, "pop_m": 4.1},
    {"name": "Salvador", "country": "Brazil", "lat": -12.9777, "lng": -38.5016, "pop_m": 3.9},
    {"name": "Fortaleza", "country": "Brazil", "lat": -3.7319, "lng": -38.5267, "pop_m": 4.0},
    {"name": "Curitiba", "country": "Brazil", "lat": -25.4284, "lng": -49.2733, "pop_m": 3.5},
    {"name": "Porto Alegre", "country": "Brazil", "lat": -30.0346, "lng": -51.2177, "pop_m": 4.1},
    {"name": "Manaus", "country": "Brazil", "lat": -3.1190, "lng": -60.0217, "pop_m": 2.3},
    {"name": "Belém", "country": "Brazil", "lat": -1.4558, "lng": -48.4902, "pop_m": 2.3},
    {"name": "Goiânia", "country": "Brazil", "lat": -16.6869, "lng": -49.2648, "pop_m": 2.5},
    {"name": "Campinas", "country": "Brazil", "lat": -22.9056, "lng": -47.0608, "pop_m": 3.2},
    {"name": "Rosario", "country": "Argentina", "lat": -32.9442, "lng": -60.6505, "pop_m": 1.3},
    {"name": "Córdoba", "country": "Argentina", "lat": -31.4201, "lng": -64.1888, "pop_m": 1.6},
    {"name": "Valparaíso", "country": "Chile", "lat": -33.0472, "lng": -71.6127, "pop_m": 1.0},
]


def _unique_cities() -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    rows = []
    for city in MILLION_CITIES:
        if city["pop_m"] < 1:
            continue
        key = (city["name"], city["country"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(city)
    return rows


def _close_on_or_before(days: list[str], target: date) -> str | None:
    wanted = target.isoformat()
    chosen = None
    for day in days:
        if day <= wanted:
            chosen = day
        else:
            break
    return chosen


def parse_daily_points(daily: dict[str, Any] | None) -> list[tuple[str, float]]:
    points: list[tuple[str, float]] = []
    payload = daily or {}
    for day, temp in zip(payload.get("time") or [], payload.get("temperature_2m_mean") or []):
        if temp is None:
            continue
        try:
            points.append((str(day), float(temp)))
        except (TypeError, ValueError):
            continue
    return points


def trends_from_points(points: list[tuple[str, float]]) -> dict[str, Any]:
    empty = {key: None for key, _ in PERIODS}
    if not points:
        return {"as_of": None, "temp_c": None, "changes": empty}
    latest_day, current = points[-1]
    by_day = {day: temp for day, temp in points}
    days = [day for day, _ in points]
    latest = date.fromisoformat(latest_day)
    changes = {}
    for key, offset in PERIODS:
        past_day = _close_on_or_before(days, latest - timedelta(days=offset))
        past = by_day.get(past_day) if past_day else None
        changes[key] = None if past is None else round(current - past, 1)
    return {"as_of": latest_day, "temp_c": round(current, 1), "changes": changes}


def _pin_color(day7: float | None) -> str:
    if day7 is None:
        return "#94a3b8"
    if day7 >= 2:
        return "#ef4444"
    if day7 >= 0.5:
        return "#fb923c"
    if day7 <= -2:
        return "#1d4ed8"
    if day7 <= -0.5:
        return "#38bdf8"
    return "#94a3b8"


def _archive_payloads(rows: list[Any]) -> list[dict[str, Any]]:
    if isinstance(rows, dict):
        return [rows]
    return [row for row in (rows or []) if isinstance(row, dict)]


def fetch_city_archive(cities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=380)
    payload = overlay_http.get_json(
        OPEN_METEO_ARCHIVE,
        timeout=REQUEST_TIMEOUT,
        headers=HEADERS,
        params={
            "latitude": ",".join(f"{city['lat']:.4f}" for city in cities),
            "longitude": ",".join(f"{city['lng']:.4f}" for city in cities),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_mean",
            "timezone": "UTC",
        },
        source="city-temps",
    )
    if payload is None:
        raise RuntimeError("Open-Meteo archive unavailable")
    return _archive_payloads(payload)


CACHE_NS = "city-temps"
_worker_guard = threading.Lock()
_worker: threading.Thread | None = None


def _city_pin(city: dict[str, Any], quote: dict[str, Any] | None = None) -> dict[str, Any]:
    quote = quote or trends_from_points([])
    return {
        **city,
        "id": f"temp-{city['name']}-{city['country']}".lower().replace(" ", "-"),
        "temp_c": quote["temp_c"],
        "changes": quote["changes"],
        "as_of": quote["as_of"],
        "color": _pin_color((quote["changes"] or {}).get("7d")),
        "source": SOURCE["name"],
        "source_url": SOURCE["url"],
    }


def _payload(quotes: dict[int, dict[str, Any]], pending: bool, status: str) -> dict[str, Any]:
    cities = _unique_cities()
    rows = []
    loaded = 0
    as_of = None
    for index, city in enumerate(cities):
        quote = quotes.get(index)
        if quote and quote.get("temp_c") is not None:
            loaded += 1
        quote = quote or trends_from_points([])
        as_of = as_of or quote["as_of"]
        rows.append(_city_pin(city, quote))
    return {
        "count": len(rows),
        "as_of": as_of,
        "cities": rows,
        "source": SOURCE,
        "pending": bool(pending),
        "loaded": loaded,
        "total": len(rows),
        "status": status,
    }


def _quotes_from_payload(payload: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    quotes: dict[int, dict[str, Any]] = {}
    for index, row in enumerate((payload or {}).get("cities") or []):
        if row.get("temp_c") is None:
            continue
        quotes[index] = {
            "temp_c": row.get("temp_c"),
            "changes": row.get("changes") or trends_from_points([])["changes"],
            "as_of": row.get("as_of"),
        }
    return quotes


def _load_city_temperatures() -> dict[str, Any]:
    cities = _unique_cities()
    quotes: dict[int, dict[str, Any]] = {}
    for offset in range(0, len(cities), BATCH_SIZE):
        batch = cities[offset:offset + BATCH_SIZE]
        try:
            payloads = fetch_city_archive(batch)
        except Exception as exc:
            log.warning("[city-temps] Open-Meteo archive failed: %s", exc)
            continue
        for index, payload in enumerate(payloads):
            quotes[offset + index] = trends_from_points(parse_daily_points(payload.get("daily")))
    status = f"City temps {len(quotes)}/{len(cities)}"
    return _payload(quotes, pending=len(quotes) < len(cities), status=status)


def _run_temps() -> None:
    cities = _unique_cities()
    quotes = _quotes_from_payload(get_stale(CACHE_NS))
    log.info("[city-temps] Fetching ERA5 trends for %s cities (batches of %s)", len(cities), BATCH_SIZE)
    for offset in range(0, len(cities), BATCH_SIZE):
        batch = cities[offset:offset + BATCH_SIZE]
        if all((offset + index) in quotes for index in range(len(batch))):
            continue
        try:
            payloads = fetch_city_archive(batch)
        except Exception as exc:
            log.warning("[city-temps] Open-Meteo archive failed: %s", exc)
            continue
        for index, payload in enumerate(payloads):
            quotes[offset + index] = trends_from_points(parse_daily_points(payload.get("daily")))
        loaded = len(quotes)
        pending = loaded < len(cities)
        status = f"City temps {loaded}/{len(cities)}"
        log.info("[city-temps] %s", status)
        store(CACHE_NS, _payload(quotes, pending, status), ttl=PENDING_TTL_SECONDS if pending else None)
    final = _payload(quotes, pending=len(quotes) < len(cities), status=f"City temps {len(quotes)}/{len(cities)}")
    store(CACHE_NS, final, ttl=PENDING_TTL_SECONDS if final["pending"] else None)
    log.info("[city-temps] Finished %s", final["status"])


def _ensure_worker() -> None:
    global _worker
    with _worker_guard:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(target=_run_temps, name="city-temps", daemon=True)
        _worker.start()


def list_city_temperatures(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        payload = _load_city_temperatures()
        store(CACHE_NS, payload)
        return payload
    current = get_stale(CACHE_NS)
    if current and current.get("pending"):
        _ensure_worker()
        return current
    fresh = get_fresh(CACHE_NS)
    if fresh is not None:
        return fresh
    stale = get_stale(CACHE_NS)
    if stale is not None:
        _ensure_worker()
        return stale
    skeleton = _payload({}, True, "City pins ready; fetching Open-Meteo trends")
    store(CACHE_NS, skeleton, ttl=PENDING_TTL_SECONDS)
    _ensure_worker()
    log.info("[city-temps] Serving %s city pins while Open-Meteo loads", skeleton["count"])
    return skeleton
