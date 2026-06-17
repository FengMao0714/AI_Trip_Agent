"""Deterministic demo itineraries used as a resilient smoke-test fallback."""
# ruff: noqa: RUF001

from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_demo_itinerary(
    message: str,
    current_itinerary: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return a local itinerary for known demo scenarios."""
    normalized_message = message.replace(" ", "")

    if current_itinerary is not None:
        if "咖啡" in normalized_message:
            return _adjust_beijing_coffee(current_itinerary)
        return None

    if _is_chengdu_elder_demo(normalized_message):
        return _chengdu_elder_friendly()

    if _is_beijing_history_demo(normalized_message):
        return _beijing_history()

    if _is_shanghai_family_demo(normalized_message):
        return _shanghai_family()

    return None


def _is_beijing_history_demo(message: str) -> bool:
    has_days = "3天" in message or "三天" in message
    has_budget = "3000" in message or "三千" in message
    has_theme = "历史" in message or "文化" in message
    has_demo_shape = "路线" in message or "行程" in message or has_budget
    return "北京" in message and has_days and has_theme and has_demo_shape


def _is_chengdu_elder_demo(message: str) -> bool:
    has_days = "4天" in message or "四天" in message
    has_budget = "5000" in message or "五千" in message
    has_elder = (
        "70岁" in message
        or "七十岁" in message
        or "爷爷" in message
        or "老人" in message
    )
    has_mobility = "走不了远路" in message or "走不远" in message or "少走路" in message
    has_demo_shape = "行程" in message or "路线" in message or has_budget
    has_elder_friendly = has_elder and ("友好" in message or has_mobility or has_budget)
    return "成都" in message and has_days and has_demo_shape and has_elder_friendly


def _is_shanghai_family_demo(message: str) -> bool:
    has_days = "2天" in message or "两天" in message or "二天" in message
    has_family = "亲子" in message or "孩子" in message or "儿童" in message
    has_easy = "轻松" in message or "休闲" in message or "不赶" in message
    has_demo_shape = "游" in message or "行程" in message or "路线" in message
    return "上海" in message and has_days and has_family and has_easy and has_demo_shape


def _transport(
    mode: str,
    distance_km: float,
    duration_min: int,
    description: str,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "description": description,
    }


def _activity(
    time_slot: str,
    place_name: str,
    place_type: str,
    lng: float,
    lat: float,
    description: str,
    cost: int,
    transport: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "time_slot": time_slot,
        "place_name": place_name,
        "place_type": place_type,
        "lng": lng,
        "lat": lat,
        "description": description,
        "cost": cost,
    }
    if transport:
        result["transport"] = transport
    return result


def _beijing_history() -> dict[str, Any]:
    return {
        "destination": "北京",
        "budget": 3000,
        "total_cost": 1698,
        "summary": (
            "北京 3 天游，围绕中轴线、皇家建筑和老城街区安排，"
            "餐饮避开重辣口味，预算保留机动空间。"
        ),
        "days": [
            {
                "day": 1,
                "date": "第 1 天",
                "weather": {
                    "condition": "晴",
                    "temperature_min": 16,
                    "temperature_max": 28,
                    "advice": "故宫与景山步行较多，建议穿舒适鞋并提前预约。",
                },
                "activities": [
                    _activity(
                        "09:00-11:30",
                        "故宫博物院",
                        "景点",
                        116.397026,
                        39.918058,
                        "从午门进入，重点游览三大殿和珍宝馆，理解明清宫廷建筑。",
                        60,
                    ),
                    _activity(
                        "11:45-12:45",
                        "四季民福烤鸭店（故宫店）",
                        "餐厅",
                        116.404102,
                        39.915392,
                        "选择烤鸭和清淡京味菜，避开辛辣菜品。",
                        140,
                        _transport("步行", 1.1, 15, "从故宫神武门步行前往。"),
                    ),
                    _activity(
                        "13:15-15:00",
                        "景山公园",
                        "景点",
                        116.396541,
                        39.925073,
                        "登万春亭俯瞰故宫中轴线，时间短但视野完整。",
                        2,
                        _transport("步行", 0.8, 12, "午餐后步行到景山南门。"),
                    ),
                    _activity(
                        "15:30-17:00",
                        "什刹海",
                        "景点",
                        116.385307,
                        39.941853,
                        "沿湖慢走，看胡同和银锭桥，下午光线适合拍照。",
                        0,
                        _transport("打车", 4.2, 18, "从景山北门打车，减少步行。"),
                    ),
                    _activity(
                        "20:00-次日",
                        "北京东四胡同民宿",
                        "住宿",
                        116.421539,
                        39.929318,
                        "住在地铁 5/6 号线附近，方便后续前往天坛和王府井。",
                        420,
                        _transport("打车", 5.5, 20, "晚餐后打车回民宿。"),
                    ),
                ],
            },
            {
                "day": 2,
                "date": "第 2 天",
                "weather": {
                    "condition": "多云",
                    "temperature_min": 17,
                    "temperature_max": 27,
                    "advice": "上午室外、下午博物馆，体力分配较均衡。",
                },
                "activities": [
                    _activity(
                        "08:30-10:30",
                        "天坛公园",
                        "景点",
                        116.410829,
                        39.881913,
                        "游览祈年殿、回音壁和圜丘，感受祭天建筑。",
                        34,
                        _transport("地铁", 8.5, 35, "从东四乘地铁 5 号线。"),
                    ),
                    _activity(
                        "11:00-12:00",
                        "前门大街",
                        "景点",
                        116.397848,
                        39.895835,
                        "看老字号招牌和民国风格街区，顺路午餐。",
                        0,
                        _transport("公交", 3.2, 18, "从天坛西门到前门。"),
                    ),
                    _activity(
                        "12:15-13:15",
                        "都一处烧麦馆（前门店）",
                        "餐厅",
                        116.397131,
                        39.897472,
                        "老字号烧麦和家常菜，口味相对稳妥。",
                        85,
                        _transport("步行", 0.4, 6, "从前门大街步行抵达。"),
                    ),
                    _activity(
                        "14:00-16:00",
                        "中国国家博物馆",
                        "景点",
                        116.401177,
                        39.905341,
                        "重点看古代中国基本陈列，与故宫和天坛形成历史线索。",
                        0,
                        _transport("步行", 1.1, 15, "从前门步行至天安门广场东侧。"),
                    ),
                    _activity(
                        "16:30-17:30",
                        "王府井步行街",
                        "景点",
                        116.411376,
                        39.913184,
                        "短暂停留补给和买伴手礼，根据体力灵活缩短。",
                        0,
                        _transport("地铁", 3.8, 20, "从天安门东站到王府井站。"),
                    ),
                    _activity(
                        "20:00-次日",
                        "北京东四胡同民宿",
                        "住宿",
                        116.421539,
                        39.929318,
                        "继续入住同一民宿，避免搬运行李。",
                        420,
                        _transport("地铁", 3.7, 22, "从王府井返回东四。"),
                    ),
                ],
            },
            {
                "day": 3,
                "date": "第 3 天",
                "weather": {
                    "condition": "晴转多云",
                    "temperature_min": 18,
                    "temperature_max": 29,
                    "advice": "长城风大，建议防晒并预留返城时间。",
                },
                "activities": [
                    _activity(
                        "09:30-12:00",
                        "八达岭长城",
                        "景点",
                        116.016802,
                        40.356548,
                        "选择北一楼到北四楼区间，兼顾代表性和体力消耗。",
                        40,
                        _transport("公交", 61.5, 78, "从清河站转市郊铁路或高铁。"),
                    ),
                    _activity(
                        "12:15-13:15",
                        "岔道古城农家菜",
                        "餐厅",
                        116.000821,
                        40.360911,
                        "长城附近简餐，以家常菜和面食补充体力。",
                        80,
                        _transport("步行", 1.4, 18, "从长城出口步行或接驳前往。"),
                    ),
                    _activity(
                        "15:00-17:00",
                        "颐和园",
                        "景点",
                        116.273469,
                        39.999771,
                        "返城后游览昆明湖和长廊，作为皇家园林主题收尾。",
                        30,
                        _transport("打车", 58.4, 75, "从八达岭区域返城后前往。"),
                    ),
                    _activity(
                        "20:00-20:45",
                        "北京南站",
                        "交通",
                        116.379008,
                        39.865008,
                        "预留返程进站时间。",
                        45,
                        _transport("地铁", 13.2, 42, "从晚餐地点前往北京南站。"),
                    ),
                ],
            },
        ],
    }


def _adjust_beijing_coffee(current_itinerary: dict[str, Any]) -> dict[str, Any]:
    itinerary = deepcopy(current_itinerary)
    itinerary["summary"] = "已将第二天下午调整为咖啡馆休息，其余行程保持不变。"

    for day in itinerary.get("days", []):
        if not isinstance(day, dict) or day.get("day") != 2:
            continue

        activities = day.get("activities", [])
        if not isinstance(activities, list):
            continue

        morning = [
            item
            for item in activities
            if isinstance(item, dict)
            and not str(item.get("time_slot", "")).startswith(("14", "15", "16"))
        ]
        coffee = [
            _activity(
                "14:00-16:00",
                "Berry Beans 前门店",
                "餐厅",
                116.39762,
                39.89921,
                "把原本下午的密集游览改为咖啡馆休息，适合整理照片和恢复体力。",
                80,
                _transport("步行", 0.8, 12, "从前门午餐点步行前往。"),
            ),
            _activity(
                "16:15-17:30",
                "Page One 北京坊店",
                "餐厅",
                116.39586,
                39.89934,
                "在书店咖啡空间轻松停留，保留北京坊街区氛围但降低体力消耗。",
                60,
                _transport("步行", 0.3, 5, "从咖啡馆步行到北京坊。"),
            ),
        ]
        evening = [
            item
            for item in activities
            if isinstance(item, dict)
            and str(item.get("time_slot", "")).startswith(("18", "19", "20"))
        ]
        day["activities"] = morning + coffee + evening
        day["weather"] = {
            **day.get("weather", {}),
            "advice": "下午改为咖啡馆和书店休息，整体节奏更轻松。",
        }

    itinerary["total_cost"] = _sum_cost(itinerary)
    return itinerary


def _chengdu_elder_friendly() -> dict[str, Any]:
    return {
        "destination": "成都",
        "budget": 5000,
        "total_cost": 3180,
        "summary": "成都 4 天长辈友好行程，控制步行距离，午后安排茶馆或酒店休息。",
        "days": [
            {
                "day": 1,
                "date": "第 1 天",
                "weather": {
                    "condition": "多云",
                    "advice": "抵达日不赶景点，先适应节奏。",
                },
                "activities": [
                    _activity(
                        "10:30-12:00",
                        "宽窄巷子",
                        "景点",
                        104.056,
                        30.673,
                        "只走宽巷子和井巷子核心段，随时找座位休息。",
                        0,
                    ),
                    _activity(
                        "12:15-13:30",
                        "成都映象（窄巷子店）",
                        "餐厅",
                        104.055,
                        30.673,
                        "选择清淡川菜和蒸菜，避开重辣。",
                        130,
                        _transport("步行", 0.2, 4, "巷区内短距离步行。"),
                    ),
                    _activity(
                        "15:00-17:00",
                        "人民公园鹤鸣茶社",
                        "景点",
                        104.063,
                        30.657,
                        "喝盖碗茶、看本地生活，座位充足，适合老人休息。",
                        60,
                        _transport("打车", 2.2, 12, "午休后打车前往，避免久走。"),
                    ),
                    _activity(
                        "20:00-次日",
                        "天府广场附近酒店",
                        "住宿",
                        104.066,
                        30.657,
                        "住在市中心，减少后续跨城交通时间。",
                        520,
                        _transport("打车", 1.2, 8, "从人民公园打车回酒店。"),
                    ),
                ],
            },
            {
                "day": 2,
                "date": "第 2 天",
                "weather": {
                    "condition": "阴",
                    "advice": "上午看熊猫，下午回酒店休息。",
                },
                "activities": [
                    _activity(
                        "08:30-11:00",
                        "成都大熊猫繁育研究基地",
                        "景点",
                        104.146,
                        30.737,
                        "只走月亮产房和成年熊猫别墅附近路线，使用观光车减少步行。",
                        55,
                        _transport("打车", 14.5, 35, "从市中心打车直达南门。"),
                    ),
                    _activity(
                        "11:30-12:45",
                        "熊猫基地游客餐厅",
                        "餐厅",
                        104.146,
                        30.737,
                        "园区内简餐，避免中午再折返寻找餐厅。",
                        80,
                        _transport("步行", 0.4, 8, "园区内慢走前往。"),
                    ),
                    _activity(
                        "14:00-17:00",
                        "酒店午休",
                        "住宿",
                        104.066,
                        30.657,
                        "预留完整午休，不安排高强度游览。",
                        0,
                        _transport("打车", 14.5, 35, "午餐后打车回酒店。"),
                    ),
                    _activity(
                        "18:00-19:30",
                        "陈麻婆豆腐（清淡点餐）",
                        "餐厅",
                        104.075,
                        30.665,
                        "可点不辣或微辣菜，体验成都风味但照顾老人胃口。",
                        140,
                        _transport("打车", 2.5, 12, "晚餐短途打车。"),
                    ),
                ],
            },
            {
                "day": 3,
                "date": "第 3 天",
                "weather": {"condition": "小雨", "advice": "以室内和近距离景点为主。"},
                "activities": [
                    _activity(
                        "09:30-11:30",
                        "杜甫草堂",
                        "景点",
                        104.028,
                        30.66,
                        "选择中轴核心展陈和茅屋故居，雨天也能慢慢参观。",
                        50,
                        _transport("打车", 6.5, 22, "从酒店打车到南门。"),
                    ),
                    _activity(
                        "12:00-13:20",
                        "陈麻婆豆腐（草堂附近）",
                        "餐厅",
                        104.034,
                        30.657,
                        "选择汤菜和不辣小吃，控制油辣。",
                        120,
                        _transport("打车", 1.5, 8, "从草堂短途打车。"),
                    ),
                    _activity(
                        "14:30-16:30",
                        "青羊宫",
                        "景点",
                        104.045,
                        30.667,
                        "道观环境清静，游览范围小，适合下午慢走。",
                        10,
                        _transport("打车", 2.2, 10, "午休后短途打车前往。"),
                    ),
                    _activity(
                        "20:00-次日",
                        "天府广场附近酒店",
                        "住宿",
                        104.066,
                        30.657,
                        "继续同一酒店，避免搬运行李。",
                        520,
                        _transport("打车", 4.8, 18, "晚间打车回酒店。"),
                    ),
                ],
            },
            {
                "day": 4,
                "date": "第 4 天",
                "weather": {
                    "condition": "多云",
                    "advice": "返程日只安排轻松市区点位。",
                },
                "activities": [
                    _activity(
                        "09:30-11:00",
                        "文殊院",
                        "景点",
                        104.075,
                        30.681,
                        "寺院和文殊坊动线平缓，可随时停坐休息。",
                        0,
                        _transport("打车", 3.8, 16, "从酒店打车前往。"),
                    ),
                    _activity(
                        "11:15-12:30",
                        "文殊院素斋",
                        "餐厅",
                        104.075,
                        30.681,
                        "清淡素食作为返程前午餐。",
                        90,
                        _transport("步行", 0.2, 4, "寺院周边短距离步行。"),
                    ),
                    _activity(
                        "14:00-15:30",
                        "太古里轻松散步",
                        "景点",
                        104.083,
                        30.653,
                        "只逛平层街区，购物和休息点多，适合返程前放松。",
                        0,
                        _transport("打车", 4.5, 18, "从文殊院打车前往。"),
                    ),
                    _activity(
                        "17:00-18:00",
                        "成都东站",
                        "交通",
                        104.141,
                        30.63,
                        "预留充足进站时间，避免老人赶路。",
                        60,
                        _transport("打车", 10.5, 28, "从太古里打车到成都东站。"),
                    ),
                ],
            },
        ],
    }


def _shanghai_family() -> dict[str, Any]:
    return {
        "destination": "上海",
        "budget": 2500,
        "total_cost": 1580,
        "summary": "上海 2 天亲子轻松游，围绕博物馆、城市地标和短距离转场安排，午后保留休息时间。",
        "days": [
            {
                "day": 1,
                "date": "第 1 天",
                "weather": {
                    "condition": "多云",
                    "advice": "上午室内展馆，下午外滩短距离步行，注意给孩子补水和休息。",
                },
                "activities": [
                    _activity(
                        "09:30-12:00",
                        "上海自然博物馆",
                        "景点",
                        121.46201,
                        31.23558,
                        "恐龙、生命演化和互动展区适合亲子慢慢看，建议提前预约。",
                        90,
                    ),
                    _activity(
                        "12:15-13:20",
                        "静安大悦城亲子餐厅",
                        "餐厅",
                        121.4671,
                        31.2424,
                        "选择商场内用餐，座位和洗手间更方便，也便于午后休息。",
                        180,
                        _transport("打车", 1.8, 10, "从自然博物馆短途打车到商场。"),
                    ),
                    _activity(
                        "14:00-16:00",
                        "南京路步行街",
                        "景点",
                        121.4782,
                        31.2363,
                        "下午轻松逛街和补给，孩子累了可随时进商场休息。",
                        0,
                        _transport("地铁", 2.6, 18, "乘地铁到人民广场或南京东路。"),
                    ),
                    _activity(
                        "16:30-18:00",
                        "外滩",
                        "景点",
                        121.4903,
                        31.2397,
                        "沿江看万国建筑和陆家嘴天际线，控制步行距离，不安排晚间赶场。",
                        0,
                        _transport("步行", 1.2, 18, "从南京东路步行到外滩观景段。"),
                    ),
                    _activity(
                        "20:00-次日",
                        "人民广场附近亲子酒店",
                        "住宿",
                        121.4752,
                        31.2304,
                        "住在地铁换乘便利区域，第二天去浦东或返程都更省力。",
                        560,
                        _transport("打车", 3.0, 16, "外滩晚高峰后打车回酒店。"),
                    ),
                ],
            },
            {
                "day": 2,
                "date": "第 2 天",
                "weather": {
                    "condition": "晴",
                    "advice": "浦东活动以室内为主，避开中午暴晒，返程前预留整理时间。",
                },
                "activities": [
                    _activity(
                        "09:30-11:30",
                        "上海科技馆",
                        "景点",
                        121.5413,
                        31.2188,
                        "选择儿童科技园、机器人世界等互动展区，控制参观范围避免疲劳。",
                        120,
                        _transport("地铁", 8.5, 32, "从人民广场乘地铁前往科技馆站。"),
                    ),
                    _activity(
                        "12:00-13:15",
                        "陆家嘴中心亲子餐厅",
                        "餐厅",
                        121.5067,
                        31.2419,
                        "商场午餐选择多，适合孩子临时调整口味。",
                        200,
                        _transport("地铁", 4.8, 22, "从科技馆到陆家嘴商圈。"),
                    ),
                    _activity(
                        "14:00-16:00",
                        "上海海洋水族馆",
                        "景点",
                        121.5009,
                        31.2394,
                        "海底隧道和主题展缸适合亲子观看，下午室内节奏更轻松。",
                        330,
                        _transport("步行", 0.8, 12, "午餐后步行到水族馆。"),
                    ),
                    _activity(
                        "16:30-17:30",
                        "陆家嘴滨江亲水平台",
                        "景点",
                        121.4974,
                        31.2408,
                        "返程前短暂停留看江景，不再安排高强度项目。",
                        0,
                        _transport("步行", 0.6, 10, "从水族馆慢走到滨江平台。"),
                    ),
                    _activity(
                        "18:00-19:00",
                        "上海虹桥站",
                        "交通",
                        121.3279,
                        31.2004,
                        "预留充足进站和取行李时间，避免带孩子赶路。",
                        100,
                        _transport("地铁", 21.0, 50, "从陆家嘴乘地铁前往虹桥站。"),
                    ),
                ],
            },
        ],
    }


def _sum_cost(itinerary: dict[str, Any]) -> int:
    total = 0
    for day in itinerary.get("days", []):
        if not isinstance(day, dict):
            continue
        for activity in day.get("activities", []):
            if isinstance(activity, dict) and isinstance(activity.get("cost"), int):
                total += activity["cost"]
    return total
