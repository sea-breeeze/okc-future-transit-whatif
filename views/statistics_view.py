"""Pure presentation functions for KPI cards and readable itinerary legs."""
from html import escape
from models.route_calculator import Itinerary
from models.statistics import TripStatistics


def kpi_html(stat: TripStatistics | None, show_comparison: bool) -> str:
    if not stat:
        return '<div class="empty-kpis">Select two connected points to see trip estimates.</div>'
    minutes = round(stat.transit_minutes)
    transfers = stat.transfers
    items = [
        ('ESTIMATED TRIP', f'{minutes} <small>min</small>', f'{stat.transit_miles:.1f} miles on transit', ''),
        ('EST. TRANSIT FARE', f'${stat.fare_usd:.2f}', 'Editable example fare', '◇'),
        ('TRANSFERS', str(transfers), 'Across shared stations', '⇄'),
    ]
    if show_comparison:
        if stat.money_saved_usd >= 0:
            items.append(('EST. MONEY SAVED', f'${stat.money_saved_usd:.2f}',
                          'Versus illustrative driving costs', '↗'))
        if stat.time_saved_minutes >= 0:
            items.append(('EST. TIME SAVED', f'{round(stat.time_saved_minutes)} <small>min</small>',
                          'Versus illustrative driving time', '◷'))
    cards = []
    for title, value, note, glyph in items:
        cards.append(
            '<div class="kpi-card">'
            f'<span class="kpi-icon">{glyph}</span><span class="kpi-label">{escape(title)}</span>'
            f'<div class="kpi-value">{value}</div><div class="kpi-note">{escape(note)}</div>'
            '</div>'
        )
    return f'<div class="kpi-grid">{"".join(cards)}</div>'


def leg_html(itinerary: Itinerary, stations, lines) -> str:
    out = []
    for i, leg in enumerate(itinerary.legs, 1):
        line = lines[leg.line_id]
        title = escape(line.name)
        start = escape(stations[leg.from_id].name)
        end = escape(stations[leg.to_id].name)
        out.append(f'''
        <div class="leg-card" style="--line:{escape(line.color)}">
          <div class="leg-top"><span class="leg-index">{i:02d}</span>
          <span class="mode-tag">{escape(line.mode.upper())}</span>
          <span class="leg-minutes">~{round(leg.minutes)} min</span></div>
          <div class="leg-title">{title}</div>
          <div class="leg-stations"><span>{start}</span><span class="leg-arrow">→</span><span>{end}</span></div>
        </div>''')
        if i < len(itinerary.legs):
            via = escape(stations[leg.to_id].name)
            out.append(f'<div class="transfer-label">⇄ &nbsp; Transfer at {via}</div>')
    return ''.join(out)
