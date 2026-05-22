"""
Sales Report Parser for JM Baryani HQ.
Parses PDF reports into structured data for analytics.
Supports: Daily Sales, FC & GP, Delivery Partner, YTD Sales reports.
"""

import re
import pdfplumber
from typing import Dict, Any, List, Optional
from datetime import datetime, date


class SalesReportParser:
    """Parse various JM Baryani sales report formats."""

    # Outlet name normalization
    OUTLET_MAP = {
        "central kitchen": "Central Kitchen",
        "subang": "JM Subang Jaya",
        "ss18": "JM Subang Jaya",
        "wangsa": "JM Wangsa Walk",
        "setia city": "JM Setia City",
        "ioi city": "JM IOI City",
    }

    def detect_report_type(self, text: str) -> str:
        """Detect the type of report from its content."""
        text_lower = text.lower()
        if "food cost and gross profit" in text_lower:
            return "fc_gp"
        elif "ytd sales" in text_lower and "outlet" not in text_lower:
            return "fc_gp_ytd"
        elif "daily sales report" in text_lower and "ytd" in text_lower:
            return "ytd_sales"
        elif "daily sales report" in text_lower:
            return "daily_sales"
        elif "outlet sales performance" in text_lower:
            return "ytd_sales"
        elif "delivery sales performance" in text_lower:
            return "delivery_detail"
        elif "delivery partner" in text_lower or "delivery revenue" in text_lower:
            return "delivery_partner"
        return "unknown"

    def parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """Parse a PDF report and return structured data."""
        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        report_type = self.detect_report_type(full_text)

        result = {
            "report_type": report_type,
            "raw_text": full_text,
            "data": {},
            "insights": []
        }

        if report_type == "fc_gp":
            result["data"] = self._parse_fc_gp(full_text)
        elif report_type == "fc_gp_ytd":
            result["data"] = self._parse_fc_gp_ytd(full_text)
        elif report_type == "daily_sales":
            result["data"] = self._parse_daily_sales(full_text)
        elif report_type == "ytd_sales":
            result["data"] = self._parse_ytd_sales(full_text)
        elif report_type == "delivery_partner":
            result["data"] = self._parse_delivery_partner(full_text)
        elif report_type == "delivery_detail":
            result["data"] = self._parse_delivery_detail(full_text)

        # Generate insights
        result["insights"] = self._generate_insights(result)

        return result

    def _parse_rm(self, value: str) -> float:
        """Parse RM value string to float."""
        if not value:
            return 0.0
        cleaned = re.sub(r'[RM,\s]', '', str(value).replace('−', '-').replace('–', '-'))
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    def _parse_pct(self, value: str) -> float:
        """Parse percentage string to float."""
        if not value:
            return 0.0
        cleaned = re.sub(r'[%\s]', '', str(value))
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    def _normalize_outlet(self, name: str) -> str:
        """Normalize outlet name."""
        name_lower = name.lower().strip()
        for key, normalized in self.OUTLET_MAP.items():
            if key in name_lower:
                return normalized
        return name.strip()

    # --- FC & GP Report Parser ---
    def _parse_fc_gp(self, text: str) -> Dict[str, Any]:
        """Parse Food Cost & Gross Profit report."""
        lines = text.strip().split('\n')
        outlets = []
        current_year = None

        for line in lines:
            # Detect month header
            month_match = re.search(r'MONTH:\s*([\w\s]+\d{4})', line, re.IGNORECASE)
            if month_match:
                current_year = month_match.group(1).strip()
                continue

            # Parse outlet lines (numbered)
            outlet_match = re.match(
                r'\d+\s+(.+?)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+([\d.]+%)\s+([\d.]+%)\s+RM([\d,.]+)',
                line
            )
            if outlet_match:
                outlet = {
                    "outlet": self._normalize_outlet(outlet_match.group(1)),
                    "period": current_year,
                    "opening_stock": self._parse_rm(outlet_match.group(2)),
                    "purchases": self._parse_rm(outlet_match.group(3)),
                    "total_stock": self._parse_rm(outlet_match.group(4)),
                    "closing_stock": self._parse_rm(outlet_match.group(5)),
                    "stock_usage": self._parse_rm(outlet_match.group(6)),
                    "total_sales": self._parse_rm(outlet_match.group(7)),
                    "daily_avg_sales": self._parse_rm(outlet_match.group(8)),
                    "food_cost_pct": self._parse_pct(outlet_match.group(9)),
                    "gross_profit_pct": self._parse_pct(outlet_match.group(10)),
                    "gross_profit_rm": self._parse_rm(outlet_match.group(11)),
                }
                outlets.append(outlet)

            # Simpler pattern for Total line
            total_match = re.match(
                r'Total\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+RM([\d,.]+)\s+([\d.]+%)\s+([\d.]+%)\s+RM([\d,.]+)',
                line
            )
            if total_match:
                outlets.append({
                    "outlet": "TOTAL",
                    "period": current_year,
                    "opening_stock": self._parse_rm(total_match.group(1)),
                    "purchases": self._parse_rm(total_match.group(2)),
                    "total_stock": self._parse_rm(total_match.group(3)),
                    "closing_stock": self._parse_rm(total_match.group(4)),
                    "stock_usage": self._parse_rm(total_match.group(5)),
                    "total_sales": self._parse_rm(total_match.group(6)),
                    "daily_avg_sales": self._parse_rm(total_match.group(7)),
                    "food_cost_pct": self._parse_pct(total_match.group(8)),
                    "gross_profit_pct": self._parse_pct(total_match.group(9)),
                    "gross_profit_rm": self._parse_rm(total_match.group(10)),
                })

        return {"outlets": outlets, "report_month": current_year}

    # --- YTD Sales Parser ---
    def _parse_fc_gp_ytd(self, text: str) -> Dict[str, Any]:
        """Parse YTD Food Cost & GP report."""
        lines = text.strip().split('\n')
        outlets = []

        for line in lines:
            # Match outlet with monthly sales
            rm_values = re.findall(r'RM([\d,.]+)', line)
            if rm_values and len(rm_values) >= 2:
                # Check if line starts with outlet indicator
                for key in self.OUTLET_MAP:
                    if key in line.lower():
                        outlet_name = self._normalize_outlet(line.split('RM')[0].strip())
                        values = [self._parse_rm(v) for v in rm_values]
                        outlets.append({
                            "outlet": outlet_name,
                            "monthly_sales": values[:-1] if len(values) > 1 else values,
                            "total": values[-1] if values else 0
                        })
                        break

        return {"outlets": outlets}

    # --- Daily Sales Parser ---
    def _parse_daily_sales(self, text: str) -> Dict[str, Any]:
        """Parse Daily Sales Report."""
        lines = text.strip().split('\n')
        daily_records = []
        total_sales = 0.0
        channel_totals = {"dine_in": 0, "takeaway": 0, "delivery": 0, "catering": 0}

        # Extract summary line
        summary_match = re.search(r'TOTAL SALES\s+RM([\d,.]+)', text)
        if summary_match:
            total_sales = self._parse_rm(summary_match.group(1))

        # Extract channel percentages
        channel_match = re.search(r'(\d+)%\s+(\d+)%\s+(\d+)%\s+(\d+)%', text)
        channel_pcts = {}
        if channel_match:
            channel_pcts = {
                "dine_in_pct": int(channel_match.group(1)),
                "takeaway_pct": int(channel_match.group(2)),
                "delivery_pct": int(channel_match.group(3)),
                "catering_pct": int(channel_match.group(4)),
            }

        # Extract channel RM values
        dine_match = re.search(r'DINE IN\s+([\d,.]+)', text)
        ta_match = re.search(r'TAKE AWAY\s+([\d,.]+)', text)
        del_match = re.search(r'DELIVERY\s+([\d,.]+)', text)
        cat_match = re.search(r'CATERING\s+([\d,.]+)', text)

        if dine_match:
            channel_totals["dine_in"] = self._parse_rm(dine_match.group(1))
        if ta_match:
            channel_totals["takeaway"] = self._parse_rm(ta_match.group(1))
        if del_match:
            channel_totals["delivery"] = self._parse_rm(del_match.group(1))
        if cat_match:
            channel_totals["catering"] = self._parse_rm(cat_match.group(1))

        # Parse daily lines
        for line in lines:
            # Match date patterns like "1-Apr-26" followed by numbers
            date_match = re.match(r'(\d{1,2}-\w{3}-\d{2})\s+(\d+)\s+', line)
            if date_match:
                date_str = date_match.group(1)
                tc = int(date_match.group(2))

                # Extract the TOTAL SALES at end of line
                total_match = re.search(r'([\d,]+\.\d{2})\s*$', line)
                daily_total = self._parse_rm(total_match.group(1)) if total_match else 0

                daily_records.append({
                    "date": date_str,
                    "transaction_count": tc,
                    "total_sales": daily_total
                })

        return {
            "total_sales": total_sales,
            "channel_totals": channel_totals,
            "channel_percentages": channel_pcts,
            "daily_records": daily_records,
            "days_count": len(daily_records)
        }

    # --- YTD Sales Performance Parser ---
    def _parse_ytd_sales(self, text: str) -> Dict[str, Any]:
        """Parse YTD Outlet Sales Performance report."""
        lines = text.strip().split('\n')
        outlets_monthly = []
        targets = []
        historical = []

        # Parse monthly sales
        for line in lines:
            if any(key in line.lower() for key in self.OUTLET_MAP.keys()):
                rm_values = re.findall(r'RM([\d,.]+)', line)
                if rm_values:
                    outlet_name = self._normalize_outlet(line.split('RM')[0].strip())
                    values = [self._parse_rm(v) for v in rm_values]
                    outlets_monthly.append({
                        "outlet": outlet_name,
                        "monthly_values": values[:-1] if len(values) > 1 else values,
                        "total": values[-1] if values else 0
                    })

        # Parse target section
        target_section = re.search(r'SALES VS TARGET(.*?)(?:SALES PERFORMANCE|$)', text, re.DOTALL | re.IGNORECASE)
        if target_section:
            for line in target_section.group(1).split('\n'):
                nums = re.findall(r'([\d,.]+\.\d{2})', line)
                if len(nums) >= 3:
                    for key in self.OUTLET_MAP:
                        if key in line.lower():
                            targets.append({
                                "outlet": self._normalize_outlet(line),
                                "breakeven": self._parse_rm(nums[0]),
                                "target": self._parse_rm(nums[1]),
                                "actual_sales": self._parse_rm(nums[2]),
                                "variance": self._parse_rm(nums[3]) if len(nums) > 3 else 0
                            })
                            break

        # Total
        total_match = re.search(r'TOTAL\s+RM([\d,.]+)', text)
        grand_total = self._parse_rm(total_match.group(1)) if total_match else 0

        return {
            "outlets_monthly": outlets_monthly,
            "targets": targets,
            "grand_total": grand_total
        }

    # --- Delivery Partner Parser ---
    def _parse_delivery_partner(self, text: str) -> Dict[str, Any]:
        """Parse Delivery Partner & Online Store Sales report."""
        lines = text.strip().split('\n')
        outlets_delivery = []
        platform_totals = []

        # Parse outlet delivery totals
        for line in lines:
            if any(key in line.lower() for key in self.OUTLET_MAP.keys()):
                nums = re.findall(r'([\d,.]+\.\d{2})', line)
                if nums:
                    outlet_name = self._normalize_outlet(line)
                    monthly_values = [self._parse_rm(n) for n in nums]
                    outlets_delivery.append({
                        "outlet": outlet_name,
                        "monthly_values": monthly_values[:-1] if len(monthly_values) > 1 else monthly_values,
                        "total": monthly_values[-1] if monthly_values else 0
                    })

        # Parse platform breakdown
        platforms = ["GRABFOOD", "ODDLE", "BEEP", "SHOPEEFOOD", "IN HOUSE", "CATERING"]
        for line in lines:
            for platform in platforms:
                if platform.lower() in line.lower():
                    nums = re.findall(r'([\d,.]+\.\d{2})', line)
                    if nums:
                        values = [self._parse_rm(n) for n in nums]
                        platform_totals.append({
                            "platform": platform.title(),
                            "monthly_values": values[:-1] if len(values) > 1 else values,
                            "total": values[-1] if values else 0
                        })
                    break

        # Grand total
        total_match = re.search(r'TOTAL\s+([\d,.]+\.\d{2})\s+([\d,.]+\.\d{2})\s+([\d,.]+\.\d{2})\s+([\d,.]+\.\d{2})', text)

        return {
            "outlets_delivery": outlets_delivery,
            "platform_totals": platform_totals,
        }

    # --- Delivery Detail Parser ---
    def _parse_delivery_detail(self, text: str) -> Dict[str, Any]:
        """Parse detailed Delivery Sales Performance report."""
        lines = text.strip().split('\n')
        outlet_platforms = []

        # Extract total
        total_sales_match = re.search(r'TOTAL SALES.*?RM\s*([\d,.]+)', text)
        total_trips_match = re.search(r'TOTAL TRIP.*?(\d+)', text)

        total_sales = self._parse_rm(total_sales_match.group(1)) if total_sales_match else 0
        total_trips = int(total_trips_match.group(1)) if total_trips_match else 0

        # Parse outlet breakdown table
        for line in lines:
            if "jm bariani" in line.lower() or "jm " in line.lower():
                nums = re.findall(r'([\d,.]+\.\d{2})', line)
                if len(nums) >= 5:
                    outlet_name = self._normalize_outlet(line)
                    outlet_platforms.append({
                        "outlet": outlet_name,
                        "grabfood": self._parse_rm(nums[0]),
                        "oddle": self._parse_rm(nums[1]),
                        "beep": self._parse_rm(nums[2]),
                        "shopee": self._parse_rm(nums[3]),
                        "inhouse": self._parse_rm(nums[4]),
                        "total": self._parse_rm(nums[5]) if len(nums) > 5 else 0
                    })

        return {
            "total_sales": total_sales,
            "total_trips": total_trips,
            "outlet_platforms": outlet_platforms
        }

    # --- Insights Generator ---
    def _generate_insights(self, result: Dict) -> List[Dict[str, Any]]:
        """Generate meaningful business insights from parsed data."""
        insights = []
        data = result.get("data", {})
        report_type = result.get("report_type", "")

        if report_type == "fc_gp":
            outlets = data.get("outlets", [])
            non_total = [o for o in outlets if o.get("outlet") != "TOTAL"]

            if non_total:
                # Best performing outlet (highest GP%)
                best_gp = max(non_total, key=lambda x: x.get("gross_profit_pct", 0))
                worst_gp = min(non_total, key=lambda x: x.get("gross_profit_pct", 0))
                highest_sales = max(non_total, key=lambda x: x.get("total_sales", 0))

                insights.append({
                    "type": "positive",
                    "title": "Best Gross Profit",
                    "message": f"{best_gp['outlet']} has the highest GP at {best_gp['gross_profit_pct']:.1f}% (RM{best_gp['gross_profit_rm']:,.0f})"
                })
                insights.append({
                    "type": "warning",
                    "title": "Lowest Gross Profit",
                    "message": f"{worst_gp['outlet']} has the lowest GP at {worst_gp['gross_profit_pct']:.1f}%. Food cost is {worst_gp['food_cost_pct']:.1f}%"
                })
                insights.append({
                    "type": "info",
                    "title": "Highest Revenue",
                    "message": f"{highest_sales['outlet']} leads with RM{highest_sales['total_sales']:,.0f} (avg RM{highest_sales['daily_avg_sales']:,.0f}/day)"
                })

                # Check if any outlet has FC > 50%
                high_fc = [o for o in non_total if o.get("food_cost_pct", 0) > 50]
                if high_fc:
                    names = ", ".join(set([o["outlet"] for o in high_fc]))
                    insights.append({
                        "type": "danger",
                        "title": "High Food Cost Alert",
                        "message": f"{names} has food cost above 50%. Review supplier pricing or portion control."
                    })

        elif report_type == "daily_sales":
            daily = data.get("daily_records", [])
            if daily:
                # Find busiest/slowest day
                if daily:
                    busiest = max(daily, key=lambda x: x.get("total_sales", 0))
                    slowest = min(daily, key=lambda x: x.get("total_sales", 0))
                    avg_daily = data.get("total_sales", 0) / len(daily) if daily else 0

                    insights.append({
                        "type": "positive",
                        "title": "Busiest Day",
                        "message": f"{busiest['date']} with RM{busiest['total_sales']:,.0f} ({busiest.get('transaction_count', 0)} transactions)"
                    })
                    insights.append({
                        "type": "warning",
                        "title": "Slowest Day",
                        "message": f"{slowest['date']} with RM{slowest['total_sales']:,.0f}"
                    })
                    insights.append({
                        "type": "info",
                        "title": "Daily Average",
                        "message": f"RM{avg_daily:,.0f} per day across all outlets"
                    })

            # Channel insights
            channels = data.get("channel_percentages", {})
            if channels:
                insights.append({
                    "type": "info",
                    "title": "Revenue Channels",
                    "message": f"Dine-in {channels.get('dine_in_pct', 0)}% | Takeaway {channels.get('takeaway_pct', 0)}% | Delivery {channels.get('delivery_pct', 0)}% | Catering {channels.get('catering_pct', 0)}%"
                })

        elif report_type == "ytd_sales":
            targets = data.get("targets", [])
            if targets:
                missed = [t for t in targets if t.get("actual_sales", 0) < t.get("target", 0)]
                if missed:
                    for t in missed:
                        shortfall = t.get("target", 0) - t.get("actual_sales", 0)
                        insights.append({
                            "type": "warning",
                            "title": f"{t['outlet']} Below Target",
                            "message": f"Short by RM{shortfall:,.0f} (Target: RM{t['target']:,.0f}, Actual: RM{t['actual_sales']:,.0f})"
                        })

            outlets = data.get("outlets_monthly", [])
            if outlets:
                highest = max(outlets, key=lambda x: x.get("total", 0))
                insights.append({
                    "type": "positive",
                    "title": "Top Performing Outlet YTD",
                    "message": f"{highest['outlet']} with RM{highest['total']:,.0f} total revenue"
                })

        elif report_type in ("delivery_partner", "delivery_detail"):
            platforms = data.get("platform_totals", [])
            if platforms:
                top_platform = max(platforms, key=lambda x: x.get("total", 0))
                insights.append({
                    "type": "info",
                    "title": "Top Delivery Platform",
                    "message": f"{top_platform['platform']} leads with RM{top_platform['total']:,.0f} total revenue"
                })

            outlet_del = data.get("outlets_delivery", []) or data.get("outlet_platforms", [])
            if outlet_del:
                top_outlet = max(outlet_del, key=lambda x: x.get("total", 0))
                insights.append({
                    "type": "positive",
                    "title": "Top Delivery Outlet",
                    "message": f"{top_outlet['outlet']} generates the most delivery revenue"
                })

        return insights


# Singleton
sales_parser = SalesReportParser()
