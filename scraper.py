import json
import os
import requests

# 168常用接口源 (澳洲幸运10: 10012, 幸运飞艇: 10057)
API_SOURCES = [
    "https://api.api68.com/pks/getPksHistoryList.do?lotCode={lot_code}",
    "https://api.1680210.com/pks/getPksHistoryList.do?lotCode={lot_code}",
    "https://168yyyy.com/api/pks/getPksHistoryList.do?lotCode={lot_code}"
]

LOT_CONFIG = {
    "au10": {"name": "澳洲幸运10", "code": "10012"},
    "ft": {"name": "幸运飞艇", "code": "10057"}
}

def fetch_raw_data(lot_code):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://168yyyy.com/"
    }
    for tpl in API_SOURCES:
        url = tpl.format(lot_code=lot_code)
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("result", {}).get("data", []) or data.get("rows", []) or data.get("data", [])
                if items:
                    return items
        except Exception:
            continue
    return []

def parse_items(items):
    """提取期号与 1~10 名车号，并取最近 30 期（按期号由旧到新排序）"""
    parsed = []
    for item in items:
        period = str(item.get("preDrawIssue") or item.get("issue") or item.get("period", ""))
        code_str = item.get("preDrawCode") or item.get("code") or item.get("numbers", "")
        if not period or not code_str:
            continue
        
        if "," in code_str:
            nums = [int(x) for x in code_str.split(",") if x.strip()]
        else:
            nums = [int(x) for x in code_str.split() if x.strip()]

        if len(nums) == 10:
            parsed.append({"period": period, "numbers": nums})

    # 按期号升序，截取最新 30 期
    parsed.sort(key=lambda x: str(x["period"]))
    return parsed[-30:]

def calculate_omits_and_stats(history_30):
    trends = []
    current_omits = [{num: 0 for num in range(1, 11)} for _ in range(10)]

    for row in history_30:
        nums = row["numbers"]
        pos_omits = []

        for pos_idx, hit_num in enumerate(nums):
            pos_dict = {}
            for n in range(1, 11):
                if n == hit_num:
                    pos_dict[str(n)] = {"hit": True, "omit": 0}
                    current_omits[pos_idx][n] = 0
                else:
                    current_omits[pos_idx][n] += 1
                    pos_dict[str(n)] = {"hit": False, "omit": current_omits[pos_idx][n]}
            pos_omits.append(pos_dict)

        trends.append({
            "period": row["period"],
            "numbers": nums,
            "sum": sum(nums[:2]),
            "span": abs(nums[0] - nums[1]),
            "positions": pos_omits
        })
    return trends

def main():
    result = {}
    for key, conf in LOT_CONFIG.items():
        raw = fetch_raw_data(conf["code"])
        history = parse_items(raw)
        
        if not history and os.path.exists("data.json"):
            try:
                with open("data.json", "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    if key in old_data:
                        result[key] = old_data[key]
                        continue
            except Exception:
                pass

        trends = calculate_omits_and_stats(history)
        result[key] = {
            "name": conf["name"],
            "code": conf["code"],
            "trends": trends
        }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("成功更新 data.json，保留最新 30 期记录。")

if __name__ == "__main__":
    main()
