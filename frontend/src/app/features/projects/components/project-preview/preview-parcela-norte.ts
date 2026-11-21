import { Component, input } from '@angular/core';

/** Schematic of the reference mockup, reproduced verbatim. */
@Component({
  selector: 'app-preview-parcela-norte',
  template: `
    <svg class="w-full h-full select-none"
          role="img"
          [attr.aria-label]="ariaLabel()" viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg">
    <!-- Parcel Boundary -->
    <rect fill="#f8faf6" height="124" rx="4" stroke="#166534" stroke-dasharray="4 2" stroke-width="2" width="290" x="25" y="18"></rect>
    <!-- 3 Cultivos Zones -->
    <rect fill="#fee2e2" height="114" opacity="0.85" rx="2" width="90" x="30" y="23"></rect>
    <rect fill="#fef08a" height="114" opacity="0.85" rx="2" width="90" x="125" y="23"></rect>
    <rect fill="#dcfce7" height="114" opacity="0.85" rx="2" width="90" x="220" y="23"></rect>
    <!-- Grid guidelines -->
    <line stroke="#0284c7" stroke-dasharray="2 2" stroke-width="1.2" x1="30" x2="310" y1="50" y2="50"></line>
    <line stroke="#0284c7" stroke-dasharray="2 2" stroke-width="1.2" x1="30" x2="310" y1="80" y2="80"></line>
    <line stroke="#0284c7" stroke-dasharray="2 2" stroke-width="1.2" x1="30" x2="310" y1="110" y2="110"></line>
    <!-- Labels in Zones -->
    <text fill="#991b1b" font-family="Inter" font-size="9" font-weight="700" text-anchor="middle" x="75" y="75">Tomate</text>
    <text fill="#b91c1c" font-family="Inter" font-size="8" text-anchor="middle" x="75" y="88">4,000 m²</text>
    <text fill="#854d0e" font-family="Inter" font-size="9" font-weight="700" text-anchor="middle" x="170" y="75">Pimiento</text>
    <text fill="#a16207" font-family="Inter" font-size="8" text-anchor="middle" x="170" y="88">3,500 m²</text>
    <text fill="#166534" font-family="Inter" font-size="9" font-weight="700" text-anchor="middle" x="265" y="75">Maíz Dulce</text>
    <text fill="#15803d" font-family="Inter" font-size="8" text-anchor="middle" x="265" y="88">3,500 m²</text>
    </svg>
  `,
})
export class PreviewParcelaNorte {
  readonly ariaLabel = input('Plano esquemático de la parcela');
}
