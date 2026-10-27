import unittest

from app import MILITARY_STANDARD, app, bmi_guidance, gauge_angle, military_guidance


class BmiAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_initial_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("了解自己的<br><em>健康狀況。</em>", page)
        self.assertIn("計算你的 BMI", page)
        self.assertIn('label for="name"', page)
        self.assertIn('name="name" type="text" autocomplete="name"', page)
        self.assertIn('value=""', page)
        self.assertNotIn('class="result-name"', page)

    def test_calculation_and_advice(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn("22.5", page)
        self.assertIn("健康體位", page)
        self.assertIn("維持均衡飲食", page)
        self.assertNotIn('class="result-name"', page)

    def test_calculation_with_name(self):
        response = self.client.post(
            "/", data={"name": "  王小明  ", "height": "170", "weight": "65"}
        )
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="王小明"', page)
        self.assertIn('class="result-name">王小明，你的 BMI 計算結果</p>', page)
        self.assertIn("22.5", page)

    def test_blank_name_is_optional(self):
        for name in ["", "   "]:
            with self.subTest(name=name):
                response = self.client.post(
                    "/", data={"name": name, "height": "170", "weight": "65"}
                )
                page = response.get_data(as_text=True)
                self.assertIn("YOUR RESULT", page)
                self.assertIn("22.5", page)
                self.assertNotIn('class="result-name"', page)

    def test_name_is_preserved_after_invalid_calculation(self):
        response = self.client.post(
            "/", data={"name": "王小明", "height": "", "weight": "65"}
        )
        page = response.get_data(as_text=True)
        self.assertIn('value="王小明"', page)
        self.assertIn('id="height-error"', page)
        self.assertNotIn("YOUR RESULT", page)

    def test_name_is_escaped(self):
        response = self.client.post(
            "/",
            data={
                "name": '"><script>alert(1)</script>',
                "height": "170",
                "weight": "65",
            },
        )
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)
        escaped_name = "&#34;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"
        self.assertIn(f'value="{escaped_name}"', page)
        self.assertIn(f'{escaped_name}，你的 BMI 計算結果</p>', page)
        self.assertIn("22.5", page)

    def test_taiwan_adult_thresholds(self):
        for bmi, category in [
            (18.4, "體重過輕"),
            (18.5, "健康體位"),
            (23.9, "健康體位"),
            (24.0, "體重過重"),
            (26.9, "體重過重"),
            (27.0, "肥胖"),
        ]:
            with self.subTest(bmi=bmi):
                self.assertEqual(bmi_guidance(bmi)["label"], category)

    def test_result_color_by_category(self):
        with self.client.get("/static/style.css") as response:
            self.assertEqual(response.status_code, 200)
            stylesheet = response.get_data(as_text=True).replace("\r\n", "\n")
        warning_rule = (
            ".result-panel.low .result-number,\n"
            ".result-panel.high .result-number,\n"
            ".result-panel.low .result-label strong,\n"
            ".result-panel.high .result-label strong { color: #b42318; }"
        )
        self.assertIn(warning_rule, stylesheet)
        for weight, tone in [
            ("18.4", "low"),
            ("18.5", "healthy"),
            ("23.9", "healthy"),
            ("24.0", "high"),
            ("26.9", "high"),
            ("27.0", "high"),
            ("18.46", "healthy"),
            ("23.96", "high"),
        ]:
            with self.subTest(weight=weight):
                response = self.client.post("/", data={"height": "100", "weight": weight})
                page = response.get_data(as_text=True)
                self.assertIn(f'class="result-panel {tone}"', page)
                self.assertIn('class="result-number"', page)

    def test_gauge_angle_mapping(self):
        for bmi, angle in [(5, -90.0), (10, -90.0), (18.5, -39.0), (24, -6.0), (25, 0.0), (27, 12.0), (40, 90.0), (55, 90.0)]:
            with self.subTest(bmi=bmi):
                self.assertEqual(gauge_angle(bmi), angle)

    def test_result_renders_gauge(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn('class="gauge"', page)
        self.assertIn('class="gauge-needle" style="transform: rotate(-15.0deg);"', page)
        for segment in ["seg-low", "seg-healthy", "seg-high", "seg-obese"]:
            self.assertIn(segment, page)

    def test_invalid_fields_do_not_produce_result(self):
        for height, weight in [("", "65"), ("0", "65"), ("abc", "65"), ("170", "-2"), ("inf", "65"), ("170", "nan"), ("1e-300", "65"), ("1e308", "65"), ("1", "1e308")]:
            with self.subTest(height=height, weight=weight):
                response = self.client.post("/", data={"height": height, "weight": weight})
                page = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('aria-invalid="true"', page)
                self.assertNotIn("YOUR RESULT", page)

    def test_input_is_escaped(self):
        response = self.client.post("/", data={"height": '<script>alert(1)</script>', "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)
        self.assertIn("請輸入大於 0", page)

    def test_military_bmi_boundaries_match_official_table(self):
        for weight, bmi, label in [
            ("43.2", "14.9", "免役體位"),
            ("43.3", "15.0", "替代役體位"),
            ("43.4", "15.0", "替代役體位"),
            ("47.3", "16.4", "替代役體位"),
            ("47.6", "16.5", "常備役體位"),
            ("47.9", "16.6", "常備役體位"),
            ("92.2", "31.9", "常備役體位"),
            ("92.5", "32.0", "常備役體位"),
            ("92.8", "32.1", "替代役體位"),
            ("100.9", "34.9", "替代役體位"),
            ("101.2", "35.0", "替代役體位"),
            ("101.5", "35.1", "免役體位"),
        ]:
            with self.subTest(weight=weight):
                result = military_guidance("170", weight)
                self.assertEqual(result["bmi"], bmi)
                self.assertEqual(result["label"], label)

        # Adjacent tenth-kilogram entries on both sides of each official cutoff.
        for height, weights in [
            ("158", ["37.3", "37.4", "41.0", "41.1", "80.0", "80.1", "87.4", "87.5"]),
            ("170", ["43.2", "43.3", "47.5", "47.6", "92.6", "92.7", "101.2", "101.3"]),
            ("195", ["56.8", "56.9", "62.5", "62.6", "121.8", "121.9", "133.2", "133.3"]),
        ]:
            labels = [
                "免役體位", "替代役體位", "替代役體位", "常備役體位",
                "常備役體位", "替代役體位", "替代役體位", "免役體位",
            ]
            for weight, label in zip(weights, labels):
                with self.subTest(height=height, weight=weight):
                    self.assertEqual(military_guidance(height, weight)["label"], label)

    def test_military_height_boundaries(self):
        for height, label in [
            ("154", "免役體位"),
            ("154.9", "免役體位"),
            ("155", "替代役體位"),
            ("155.1", "替代役體位"),
            ("156", "替代役體位"),
            ("157", "替代役體位"),
            ("157.9", "替代役體位"),
            ("158", "常備役體位"),
            ("158.1", "常備役體位"),
            ("195", "常備役體位"),
            ("195.9", "常備役體位"),
            ("196", "免役體位"),
            ("196.1", "免役體位"),
        ]:
            with self.subTest(height=height):
                self.assertEqual(military_guidance(height, "65")["label"], label)

    def test_short_height_bmi_exceptions_match_official_table(self):
        for height, weights in [
            ("155", ["35.9", "36.0", "84.2", "84.3"]),
            ("156", ["36.3", "36.4", "85.2", "85.3"]),
            ("157", ["36.8", "36.9", "86.3", "86.4"]),
        ]:
            for weight, label in zip(
                weights, ["免役體位", "替代役體位", "替代役體位", "免役體位"]
            ):
                with self.subTest(height=height, weight=weight):
                    self.assertEqual(military_guidance(height, weight)["label"], label)

    def test_military_measurement_truncation_and_half_up_rounding(self):
        result = military_guidance("170.9", "47.69")
        self.assertEqual(result["height"], "170")
        self.assertEqual(result["weight"], "47.6")
        self.assertEqual(result["bmi"], "16.5")
        self.assertEqual(result["label"], "常備役體位")
        result = military_guidance("170.99999999999999999999", "47.59999999999999999999")
        self.assertEqual(result["height"], "170")
        self.assertEqual(result["weight"], "47.5")
        self.assertEqual(result["label"], "替代役體位")
        result = military_guidance("170", "47.5" + "9" * 100)
        self.assertEqual(result["weight"], "47.5")
        self.assertEqual(result["label"], "替代役體位")
        for weight, expected in [("80.19", "20.0"), ("80.2", "20.1"), ("80.3", "20.1")]:
            with self.subTest(weight=weight):
                self.assertEqual(military_guidance("200", weight)["bmi"], expected)

    def test_military_result_source_and_limits(self):
        page = self.client.post(
            "/", data={"height": "170", "weight": "65"}
        ).get_data(as_text=True)
        self.assertIn('id="military-title"', page)
        self.assertIn("依身高、體重初判：<strong>常備役體位</strong>", page)
        self.assertIn("<dt>兵役 BMI</dt><dd>22.5</dd>", page)
        self.assertIn(MILITARY_STANDARD["url"], page)
        self.assertIn(MILITARY_STANDARD["table_url"].replace("&", "&amp;"), page)
        self.assertIn(MILITARY_STANDARD["version"], page)
        self.assertIn(MILITARY_STANDARD["checked_on"], page)
        self.assertIn("僅供役齡男子", page)
        self.assertIn("正式體位仍以主管機關體檢及判定為準", page)
        self.assertIn("規則不會即時連線更新", page)

    def test_military_result_refreshes_without_changing_health_calculation(self):
        for weight, bmi, military_bmi, label in [
            ("47.69", "16.3", "16.5", "常備役體位"),
            ("43.2", "14.8", "14.9", "免役體位"),
        ]:
            with self.subTest(weight=weight):
                page = self.client.post(
                    "/", data={"height": "170.9", "weight": weight}
                ).get_data(as_text=True)
                self.assertIn(f'class="result-number">{bmi}</span>', page)
                self.assertIn("你的體位屬於 <strong>體重過輕</strong>", page)
                self.assertIn(f"<dt>兵役 BMI</dt><dd>{military_bmi}</dd>", page)
                self.assertIn(f"依身高、體重初判：<strong>{label}</strong>", page)
                self.assertIn(f'value="{weight}"', page)
        page = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('id="military-title"', page)

    def test_invalid_input_never_produces_military_prediction(self):
        for height, weight in [
            ("", "65"), ("0", "65"), ("-1", "65"), ("abc", "65"),
            ("inf", "65"), ("nan", "65"), ("170", ""), ("170", "0"),
            ("170", "-1"), ("170", "abc"), ("170", "inf"), ("170", "nan"),
        ]:
            with self.subTest(height=height, weight=weight):
                result = military_guidance(height, weight)
                self.assertIsNone(result["label"])
                self.assertIsNone(result["bmi"])
                self.assertIn("資料不足", result["reason"])
                page = self.client.post(
                    "/", data={"height": height, "weight": weight}
                ).get_data(as_text=True)
                self.assertIn('aria-invalid="true"', page)
                self.assertNotIn('id="military-title"', page)
                self.assertNotIn("依身高、體重初判：", page)

    def test_military_unavailable_does_not_hide_valid_health_result(self):
        for height, weight in [("0.9", "65"), ("170", "0.09")]:
            with self.subTest(height=height, weight=weight):
                page = self.client.post(
                    "/", data={"height": height, "weight": weight}
                ).get_data(as_text=True)
                self.assertIn("YOUR RESULT", page)
                self.assertIn("無法提供兵役初步判斷", page)
                self.assertIn("依兵役量測規則處理後，身高或體重為 0", page)
                self.assertNotIn("依身高、體重初判：", page)

    def test_military_large_finite_values_do_not_crash(self):
        for height, weight in [("170", "1e308"), ("1e100", "65")]:
            with self.subTest(height=height, weight=weight):
                response = self.client.post("/", data={"height": height, "weight": weight})
                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    "依身高、體重初判：<strong>免役體位</strong>",
                    response.get_data(as_text=True),
                )


if __name__ == "__main__":
    unittest.main()
