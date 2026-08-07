# AGENT GUIDELINES & PROJECT SPECIFICATIONS

## 🚀 Project Overview
- **Project Name**: F5 Demo Application
- **Purpose**: Interactive demonstration web app designed to showcase our enterprise AI & security solutions to stakeholders and clients. Application must be vulnerable to HTTP and SQL attacks.
- **Key Focus**: High visual impact ("WOW" factor), responsive design, interactive sandboxes, and smooth performance.

---

## 🛠️ Tech Stack & Constraints

- **Core**: HTML5, Modern ES6+ JavaScript, Vanilla CSS (Custom Properties / Design Tokens).
- **Icons**: Lucide Icons or SVG icons embedded directly.
- **Charts / Visualizations**: Chart.js or Canvas API (lightweight, zero unnecessary dependencies).
- **Fonts**: Google Fonts (`Outfit` for headings, `Inter` for body).
- **No Heavy Frameworks**: Avoid bulky framework boilerplate unless explicitly requested.
- **Database**: SQL database in order to send SQL attacks
- **Deployment**: app must be deployed through Docker Compose

---

## 🎨 Design System & Aesthetic Standards

To ensure a cohesive, premium look across all components:

### 🎨 F5 Design System & Color Palette
All UI components MUST adhere to the following F5 Brand CSS Variables:

```css
{
  /* F5 Brand Palette */
  --f5-red-primary: #E4002B;       /* Iconic F5 Red */
  --f5-red-hover: #C20024;         /* Darker Red for active states */
  --f5-red-glow: rgba(228, 0, 43, 0.35); /* Glow / Focus states */
  --f5-cyber-coral: #FF2A4B;       /* Highlight & secondary badges */
  /* Typography Colors */
  --text-primary: #FFFFFF;         /* Primary text */
  --text-secondary: #94A3B8;       /* Muted subtext & labels */
  --text-accent: #FF2A4B;          /* Red text highlights */
  /* Status Indicators */
  --status-success: #10B981;       /* Active / Healthy */
  --status-warning: #F59E0B;       /* Alert / Pending */
}
```

### UI Patterns & FX
- **Glassmorphism**: Use `backdrop-filter: blur(12px)` with subtle semi-transparent borders for cards and modals.
- **Gradients**: Use vibrant 2-color linear gradients for primary action buttons, titles, and active indicators.
- **Micro-Animations**: All interactive buttons, tabs, and hover cards MUST have smooth CSS transitions (`transition: all 0.2s ease`).

---

## 💻 Code Style & Architecture Rules

1. **Modular CSS**:
   - Store global design tokens, reset, and utility classes in `css/variables.css` or top of `styles.css`.
   - Do not hardcode magic numbers or hex codes directly in component styles; always reference CSS variables (e.g., `var(--bg-primary)`).

2. **Clean Component Logic**:
   - Keep JavaScript modular. Separate mock data generation, UI rendering, and event handlers.
   - Use descriptive function and variable names (`renderMetricsDashboard()` instead of `draw()`).

3. **No Placeholders**:
   - Never leave `// TODO` or empty placeholder blocks in demo logic. Always provide functional mock data or working fallback interactions.

4. **Full API driven**
   - All pages and all actions must be through API Calls

---

## 🧪 Verification & Quality Checklist

Before completing any task, ensure:
1. **Interactive Feedback**: Every button, input, and tab provides visual hover, focus, and active feedback.
2. **Responsive Test**: Layout renders cleanly on desktop, tablet, and mobile breakpoints (`@media (max-width: 768px)`).
3. **Console Cleanliness**: Zero JavaScript runtime errors or broken asset warnings in the browser console.
4. **Demonstration Flow**: The user can successfully complete the demo scenario end-to-end without getting stuck.