import math
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, localcontext

from flask import Flask, render_template, request

app = Flask(__name__)


def bmi_guidance(bmi):
    if bmi < 18.5:
        return {
            "label": "體重過輕",
            "tone": "low",
            "advice": "留意是否攝取足夠且均衡的營養，規律進食並搭配適度肌力活動；若體重持續下降，建議諮詢醫師或營養師。",
        }
    if bmi < 24:
        return {
            "label": "健康體位",
            "tone": "healthy",
            "advice": "維持均衡飲食與規律運動，並持續留意睡眠及生活習慣，幫助保持健康體位。",
        }
    if bmi < 27:
        return {
            "label": "體重過重",
            "tone": "high",
            "advice": "可從減少含糖飲料、增加蔬菜與日常活動量開始，循序建立適合自己的健康習慣。",
        }
    return {
        "label": "肥胖",
        "tone": "high",
        "advice": "建議與醫師或營養師討論適合自己的飲食及運動計畫，並留意血壓、血糖等健康指標。",
    }


GAUGE_MIN_BMI = 10
GAUGE_MAX_BMI = 40


def gauge_angle(bmi):
    """Map a BMI value onto the half-circle gauge needle angle (-90° to 90°)."""
    clamped = min(max(bmi, GAUGE_MIN_BMI), GAUGE_MAX_BMI)
    fraction = (clamped - GAUGE_MIN_BMI) / (GAUGE_MAX_BMI - GAUGE_MIN_BMI)
    return round(-90 + 180 * fraction, 1)


def parse_positive_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


MILITARY_STANDARD = {
    "version": "民國 112 年 5 月 30 日（2023-05-30）修正發布",
    "checked_on": "2026-10-27",
    "url": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=F0040018",
    "table_url": "https://law.moj.gov.tw/LawClass/LawGetFile.ashx?FileId=0000342747&lan=C",
}


def military_guidance(height, weight):
    unavailable = {
        "label": None,
        "bmi": None,
        "reason": "資料不足，請提供大於 0 的有效身高與體重。",
    }
    if parse_positive_number(height) is None or parse_positive_number(weight) is None:
        return unavailable

    measured_height = Decimal(str(height)).to_integral_value(rounding=ROUND_DOWN)
    weight_decimal = Decimal(str(weight))
    with localcontext() as context:
        context.prec = max(28, weight_decimal.adjusted() + 7)
        measured_weight = weight_decimal.quantize(Decimal("0.1"), rounding=ROUND_DOWN)
        if measured_height == 0 or measured_weight == 0:
            return {
                **unavailable,
                "reason": "依兵役量測規則處理後，身高或體重為 0，無法提供兵役初步判斷。",
            }

        # Legal truncation and half-up rounding differ from the health BMI display.
        bmi = measured_weight / (measured_height / 100) ** 2
        bmi = bmi.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    result = {
        "height": f"{measured_height:.0f}",
        "weight": f"{measured_weight:.1f}",
        "bmi": f"{bmi:.1f}",
    }
    if measured_height < 155 or measured_height >= 196:
        label = "免役體位"
        reason = "採計身高為 154 公分以下或 196 公分以上。"
    elif bmi < 15 or bmi > 35:
        label = "免役體位"
        reason = "兵役 BMI 小於 15 或大於 35。"
    elif measured_height <= 157:
        label = "替代役體位"
        reason = "採計身高為 155 至 157 公分，且兵役 BMI 為 15 至 35（含端點）。"
    elif bmi < Decimal("16.5") or bmi > 32:
        label = "替代役體位"
        reason = "兵役 BMI 為 15 至未滿 16.5，或大於 32 至 35。"
    else:
        label = "常備役體位"
        reason = "採計身高為 158 至 195 公分，且兵役 BMI 為 16.5 至 32（含端點）。"
    return {**result, "label": label, "reason": reason}


@app.route("/", methods=["GET", "POST"])
def index():
    name_input = ""
    height_input = ""
    weight_input = ""
    errors = {}
    result = None

    if request.method == "POST":
        name_input = request.form.get("name", "").strip()
        height_input = request.form.get("height", "").strip()
        weight_input = request.form.get("weight", "").strip()
        height = parse_positive_number(height_input)
        weight = parse_positive_number(weight_input)

        if height is None:
            errors["height"] = "請輸入大於 0 的有效身高（公分）。"
        if weight is None:
            errors["weight"] = "請輸入大於 0 的有效體重（公斤）。"

        if not errors:
            height_meters = height / 100
            height_squared = height_meters * height_meters
            if not math.isfinite(height_squared) or height_squared == 0:
                errors["height"] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
            else:
                bmi = weight / height_squared
                if not math.isfinite(bmi) or bmi == 0:
                    errors["weight"] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
                else:
                    displayed_bmi = round(bmi, 1)
                    result = {
                        "bmi": f"{displayed_bmi:.1f}",
                        "gauge_angle": gauge_angle(displayed_bmi),
                        **bmi_guidance(displayed_bmi),
                        "military": military_guidance(height_input, weight_input),
                    }

    return render_template(
        "index.html",
        name_input=name_input,
        height_input=height_input,
        weight_input=weight_input,
        errors=errors,
        result=result,
        military_standard=MILITARY_STANDARD,
    )


if __name__ == "__main__":
    app.run(debug=True)
