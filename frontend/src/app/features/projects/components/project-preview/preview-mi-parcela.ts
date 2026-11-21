import { Component, input } from '@angular/core';

/** Schematic of the reference mockup, reproduced verbatim. */
@Component({
  selector: 'app-preview-mi-parcela',
  template: `
    <svg class="w-full h-full select-none"
          role="img"
          [attr.aria-label]="ariaLabel()" viewBox="0 0 340 160" xmlns="http://www.w3.org/2000/svg">
    <!-- Parcel Boundary -->
    <polygon fill="#f8faf6" points="20,15 315,15 260,145 20,145" stroke="#166534" stroke-dasharray="4 2" stroke-width="2"></polygon>
    <!-- Potato Block (70%) -->
    <polygon fill="#fef3c7" opacity="0.85" points="25,20 220,20 200,140 25,140"></polygon>
    <!-- Lettuce Block (30%) -->
    <polygon fill="#dcfce7" opacity="0.85" points="225,20 310,20 255,140 205,140"></polygon>
    <!-- Drip Lines Papa -->
    <line stroke="#0284c7" stroke-width="1.8" x1="35" x2="210" y1="40" y2="40"></line>
    <line stroke="#0284c7" stroke-width="1.8" x1="35" x2="205" y1="65" y2="65"></line>
    <line stroke="#0284c7" stroke-width="1.8" x1="35" x2="200" y1="90" y2="90"></line>
    <line stroke="#0284c7" stroke-width="1.8" x1="35" x2="195" y1="115" y2="115"></line>
    <!-- Drip Lines Lettuce -->
    <line stroke="#0284c7" stroke-width="1.8" x1="225" x2="295" y1="45" y2="45"></line>
    <line stroke="#0284c7" stroke-width="1.8" x1="220" x2="280" y1="75" y2="75"></line>
    <line stroke="#0284c7" stroke-width="1.8" x1="215" x2="265" y1="105" y2="105"></line>
    <!-- Main Pipe (Blue) -->
    <line stroke="#0369a1" stroke-width="3" x1="12" x2="12" y1="148" y2="20"></line>
    <line stroke="#0369a1" stroke-width="3" x1="12" x2="25" y1="20" y2="20"></line>
    <!-- Water Source Symbol -->
    <rect fill="#0284c7" height="18" rx="3" width="18" x="2" y="130"></rect>
    <text fill="#ffffff" font-family="Inter" font-size="9" font-weight="700" text-anchor="middle" x="11" y="142">T</text>
    <!-- Valve icons -->
    <circle cx="28" cy="40" fill="#dc2626" r="3.5"></circle>
    <circle cx="28" cy="90" fill="#dc2626" r="3.5"></circle>
    <circle cx="218" cy="45" fill="#dc2626" r="3.5"></circle>
    <!-- Labels in SVG -->
    <rect fill="#ffffff" height="28" opacity="0.9" rx="6" width="86" x="65" y="60"></rect>
    <text fill="#78350f" font-family="Inter" font-size="10" font-weight="700" text-anchor="middle" x="108" y="73">Papa (70%)</text>
    <text fill="#92400e" font-family="Inter" font-size="8" text-anchor="middle" x="108" y="84">2.240 m²</text>
    <rect fill="#ffffff" height="28" opacity="0.9" rx="6" width="70" x="220" y="60"></rect>
    <text fill="#14532d" font-family="Inter" font-size="10" font-weight="700" text-anchor="middle" x="255" y="73">Lechuga</text>
    <text fill="#166534" font-family="Inter" font-size="8" text-anchor="middle" x="255" y="84">960 m² (30%)</text>
    </svg>
  `,
})
export class PreviewMiParcela {
  readonly ariaLabel = input('Plano esquemático de la parcela');
}
