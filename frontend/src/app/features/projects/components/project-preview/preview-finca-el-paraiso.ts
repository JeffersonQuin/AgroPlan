import { Component, input } from '@angular/core';

/** Schematic of the reference mockup, reproduced verbatim. */
@Component({
  selector: 'app-preview-finca-el-paraiso',
  template: `
    <svg class="w-full h-full select-none"
          role="img"
          [attr.aria-label]="ariaLabel()" viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg">
    <!-- Parcel Boundary Trapezoid -->
    <polygon fill="#f8faf6" points="40,20 290,30 250,135 60,135" stroke="#166534" stroke-dasharray="4 2" stroke-width="2"></polygon>
    <polygon fill="#fef3c7" opacity="0.75" points="45,25 170,30 160,130 65,130"></polygon>
    <polygon fill="#e0f2fe" opacity="0.75" points="175,30 285,35 245,130 165,130"></polygon>
    <circle cx="80" cy="50" fill="#15803d" opacity="0.3" r="12"></circle>
    <circle cx="120" cy="50" fill="#15803d" opacity="0.3" r="12"></circle>
    <circle cx="80" cy="90" fill="#15803d" opacity="0.3" r="12"></circle>
    <circle cx="120" cy="90" fill="#15803d" opacity="0.3" r="12"></circle>
    <line stroke="#0284c7" stroke-width="2.5" x1="40" x2="290" y1="20" y2="30"></line>
    <circle cx="170" cy="27" fill="#dc2626" r="4"></circle>
    <text fill="#78350f" font-family="Inter" font-size="9" font-weight="700" text-anchor="middle" x="105" y="75">Nogales</text>
    <text fill="#0369a1" font-family="Inter" font-size="9" font-weight="700" text-anchor="middle" x="215" y="75">Microaspersión</text>
    </svg>
  `,
})
export class PreviewFincaElParaiso {
  readonly ariaLabel = input('Plano esquemático de la parcela');
}
