"""Offline aggregate report; no CDN, raw comments or user identifiers."""
from html import escape


def render_report(weekly, manifest):
    fields = ["week", "comments", "authors", "reply_edges", "usable_reply_rate",
              "multi_article_rate", "largest_component_fraction", "label_coverage",
              "cross_rate", "cross_hostile_rate", "cross_observed_expected", "null_status"]
    def fmt(value):
        if value is None:
            return "미측정"
        return f"{value:.3f}" if isinstance(value, float) else str(value)
    header = "".join(f"<th>{f}</th>" for f in fields)
    body = "".join("<tr>" + "".join(f"<td>{escape(fmt(r[f]))}</td>" for f in fields) + "</tr>" for r in weekly)
    return f'''<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>M2 Research — 주간 진단</title>
<style>body{{font-family:system-ui,sans-serif;background:#f5f7fb;color:#172536;margin:3rem}}
h1{{font-size:1.8rem}}.scroll{{overflow:auto;background:white;padding:1rem;border-radius:12px}}
table{{border-collapse:collapse;font-variant-numeric:tabular-nums}}th,td{{padding:.7rem;border-bottom:1px solid #ddd;text-align:right;white-space:nowrap}}
th{{background:#e9eff5}}p{{max-width:80ch;line-height:1.7}}</style>
<h1>뉴스 댓글 연구 · 주간 진단</h1>
<p>댓글 {manifest['comments']:,}건 · 사용 가능한 답글 {manifest['reply_edges']:,}건 · 중복 제거 {manifest['duplicate_rows_removed']:,}건</p>
<p>월요일 시작, 한국 시간(UTC+09:00) 기준. 정치 성향이 확인된 간선에서만 교류율을 계산합니다.
라벨 누락은 중립 또는 0으로 해석하지 않습니다. 답글은 기록된 부모 댓글과의 관계이며 실제 의미상 응답 대상과 다를 수 있습니다.</p>
<div class="scroll"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>
<p>무작위 기준은 기사·주별 발신/수신 활동량과 시간 순서를 보존하는 파일럿 MCMC입니다.
교환 불가능하거나 표본 분산이 0인 경우 비율을 미측정으로 표시합니다. 수렴 검증이나 인과 추론 결과가 아닙니다.
주간 행이 없는 기간은 수집 여부를 알 수 없으므로 0으로 채우지 않습니다.</p></html>'''
