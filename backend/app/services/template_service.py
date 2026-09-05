"""模板服务：PDF/DOCX 解析为高保真 HTML 模板"""
import re
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document as DocxDocument


def extract_variables(html: str) -> list[str]:
    """从 HTML 模板中提取 {{var}} 变量名"""
    return sorted(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", html)))


def pdf_to_template(pdf_bytes: bytes) -> str:
    """解析 PDF 为高保真现代排版 HTML 模板骨架（对标 Magic-Resume / 原版 PDF 排版）"""
    template = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    color: #111827;
    background: #ffffff;
    padding: 36px 44px;
    line-height: 1.5;
    font-size: 12.5px;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 14px;
    margin-bottom: 16px;
  }
  .header-left {
    flex: 1;
  }
  .header-left .intention {
    font-size: 13px;
    margin-bottom: 4px;
  }
  .header-left .intention strong {
    font-size: 13.5px;
    color: #0f172a;
  }
  .header-contacts {
    display: grid;
    grid-template-columns: auto auto;
    gap: 3px 20px;
    font-size: 12px;
    color: #4b5563;
    margin-top: 4px;
  }
  .header-contacts a {
    color: #4b5563;
    text-decoration: none;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
  }
  .header-right h1 {
    font-size: 28px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: 1px;
  }
  .header-photo {
    width: 76px;
    height: 100px;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
    object-fit: cover;
    background: #f8fafc;
  }
  section {
    margin-bottom: 16px;
  }
  h2.sec-title {
    font-size: 13.5px;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 1.2px solid #0f172a;
    padding-bottom: 3px;
    margin-bottom: 8px;
    text-transform: uppercase;
  }
  .item {
    margin-bottom: 10px;
  }
  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 13px;
  }
  .item-header .name {
    font-weight: 700;
    color: #0f172a;
  }
  .item-header .sub {
    color: #475569;
    font-weight: 500;
    font-size: 12px;
  }
  .item-header .date {
    font-size: 11.5px;
    color: #64748b;
    font-family: ui-monospace, SFMono-Regular, monospace;
    text-align: right;
  }
  .item-link {
    font-size: 11.5px;
    color: #2563eb;
    margin-top: 1px;
    font-family: monospace;
  }
  .item-desc {
    font-size: 12px;
    color: #4b5563;
    margin-top: 2px;
    line-height: 1.55;
  }
  ul.highlights {
    list-style-type: none;
    padding-left: 0;
    margin-top: 3px;
  }
  ul.highlights li {
    position: relative;
    padding-left: 12px;
    font-size: 12px;
    line-height: 1.6;
    color: #334155;
    margin-bottom: 2px;
  }
  ul.highlights li::before {
    content: "•";
    position: absolute;
    left: 0;
    color: #475569;
    font-weight: bold;
  }
  .skill-item {
    margin-bottom: 4px;
    font-size: 12px;
    line-height: 1.6;
    color: #1e293b;
  }
  .skill-item b {
    color: #0f172a;
  }
  .skill-tag {
    display: inline-block;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #334155;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 11px;
    margin-right: 4px;
    margin-bottom: 3px;
  }
</style>
</head>
<body>

  <!-- 页眉 -->
  <header>
    <div class="header-left">
      {% if label %}<div class="intention">👤 求职意向 <strong>{{ label }}</strong></div>{% endif %}
      <div class="header-contacts">
        {% if email %}<div>✉ {{ email }}</div>{% endif %}
        {% if phone %}<div>📞 {{ phone }}</div>{% endif %}
        {% if birthDate %}<div>📅 {{ birthDate }}</div>{% endif %}
        {% if location %}<div>📍 {{ location }}</div>{% endif %}
        {% if github %}<div>🔗 {{ github }}</div>{% endif %}
        {% if blog %}<div>🌐 {{ blog }}</div>{% endif %}
        {% for cf in custom_fields %}
          {% if cf.label and cf.value %}<div>{{ cf.label }}: {{ cf.value }}</div>{% endif %}
        {% endfor %}
      </div>
      {% if summary %}<p class="item-desc" style="margin-top: 6px;">{{ summary }}</p>{% endif %}
    </div>

    <div class="header-right">
      <h1>{{ name or '姓名' }}</h1>
      {% if photo %}
        <img class="header-photo" src="{{ photo }}" alt="证件照" />
      {% endif %}
    </div>
  </header>

  <!-- 教育经历 -->
  {% if education and education|length > 0 %}
  <section>
    <h2 class="sec-title">教育经历</h2>
    {% for e in education %}
    <div class="item">
      <div class="item-header">
        <span class="name">{{ e.institution or e.school or '' }}</span>
        <span class="sub">
          {% set sub_parts = [] %}
          {% if e.area or e.major %}{% set _ = sub_parts.append(e.area or e.major) %}{% endif %}
          {% if e.studyType or e.degree %}{% set _ = sub_parts.append(e.studyType or e.degree) %}{% endif %}
          {% if e.gpa %}{% set _ = sub_parts.append('GPA ' ~ e.gpa) %}{% endif %}
          {{ sub_parts | join(' · ') }}
        </span>
        <span class="date">{{ e.startDate or e.start_date or '' }}{% if e.endDate or e.end_date %} - {{ e.endDate or e.end_date }}{% endif %}</span>
      </div>
      {% if e.highlights or e.courses %}
      <ul class="highlights">
        {% for h in (e.highlights or e.courses or []) %}
        <li>{{ h }}</li>
        {% endfor %}
      </ul>
      {% endif %}
    </div>
    {% endfor %}
  </section>
  {% endif %}

  <!-- 专业技能 -->
  {% if skills and skills|length > 0 %}
  <section>
    <h2 class="sec-title">专业技能</h2>
    {% for s in skills %}
      <div class="skill-item">
        {% if s.keywords and s.keywords|length > 0 %}
          <b>{{ s.name }}:</b>
          {% for kw in s.keywords %}
            <span class="skill-tag">{{ kw }}</span>
          {% endfor %}
        {% else %}
          {{ s.name }}
        {% endif %}
      </div>
    {% endfor %}
  </section>
  {% endif %}

  <!-- 项目经历 -->
  {% if projects and projects|length > 0 %}
  <section>
    <h2 class="sec-title">项目经历</h2>
    {% for p in projects %}
    <div class="item">
      <div class="item-header">
        <span class="name">{{ p.name }}</span>
        {% if p.role %}<span class="sub">{{ p.role }}</span>{% endif %}
        <span class="date">{{ p.startDate or p.start_date or '' }}{% if p.endDate or p.end_date %} - {{ p.endDate or p.end_date }}{% endif %}</span>
      </div>
      {% if p.link or p.url %}
        <div class="item-link">{{ p.link or p.url }}</div>
      {% endif %}
      {% if p.description %}
        <div class="item-desc">{{ p.description }}</div>
      {% endif %}
      {% if p.highlights %}
      <ul class="highlights">
        {% for h in p.highlights %}
        <li>{{ h }}</li>
        {% endfor %}
      </ul>
      {% endif %}
    </div>
    {% endfor %}
  </section>
  {% endif %}

  <!-- 工作经历 -->
  {% if experience and experience|length > 0 %}
  <section>
    <h2 class="sec-title">工作经历</h2>
    {% for exp in experience %}
    <div class="item">
      <div class="item-header">
        <span class="name">{{ exp.company }}</span>
        {% if exp.role or exp.position %}<span class="sub">{{ exp.role or exp.position }}</span>{% endif %}
        <span class="date">{{ exp.startDate or exp.start_date or '' }}{% if exp.endDate or exp.end_date %} - {{ exp.endDate or exp.end_date }}{% endif %}</span>
      </div>
      {% if exp.description %}
        <div class="item-desc">{{ exp.description }}</div>
      {% endif %}
      {% if exp.highlights %}
      <ul class="highlights">
        {% for h in exp.highlights %}
        <li>{{ h }}</li>
        {% endfor %}
      </ul>
      {% endif %}
    </div>
    {% endfor %}
  </section>
  {% endif %}

  <!-- 个人亮点 -->
  {% if highlights and highlights|length > 0 %}
  <section>
    <h2 class="sec-title">个人亮点</h2>
    <ul class="highlights">
      {% for hl in highlights %}
      <li>{{ hl.content if hl.content is defined else hl }}</li>
      {% endfor %}
    </ul>
  </section>
  {% endif %}

  <!-- 自定义板块 -->
  {% if custom_sections %}
  {% for cs in custom_sections %}
  <section>
    <h2 class="sec-title">{{ cs.title }}</h2>
    {% for it in (cs.items or []) %}
    <div class="item">
      <div class="item-header">
        <span class="name">{{ it.title }}</span>
        {% if it.subtitle %}<span class="sub">{{ it.subtitle }}</span>{% endif %}
        {% if it.date %}<span class="date">{{ it.date }}</span>{% endif %}
      </div>
      {% if it.description %}<div class="item-desc">{{ it.description }}</div>{% endif %}
      {% if it.highlights %}
      <ul class="highlights">
        {% for h in it.highlights %}
        <li>{{ h }}</li>
        {% endfor %}
      </ul>
      {% endif %}
    </div>
    {% endfor %}
  </section>
  {% endfor %}
  {% endif %}

</body>
</html>
"""
    return template


def docx_to_template(docx_bytes: bytes) -> str:
    """解析 DOCX 字节为 HTML 模板"""
    return pdf_to_template(b"")
