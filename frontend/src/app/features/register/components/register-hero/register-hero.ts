import { Component } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matArchitectureOutline,
  matEcoOutline,
  matPrecisionManufacturingOutline,
  matSummarizeOutline,
  matValveOutline,
} from '@ng-icons/material-symbols/outline';

/**
 * Typed map from the feature key to the icon name registered in `provideIcons`.
 *
 * The value must be the registry key, never the imported SVG constant: `NgIcon`
 * normalises the `name` it receives and looks it up in the registry, so a
 * constant leaves the slot empty. Keeping semantic keys here means the template
 * binds the mapped value instead of `feature.icon`.
 */
const FEATURE_ICONS = {
  architecture: 'matArchitectureOutline',
  eco: 'matEcoOutline',
  valve: 'matValveOutline',
  summarize: 'matSummarizeOutline',
} as const satisfies Record<string, string>;

interface HeroFeature {
  icon: keyof typeof FEATURE_ICONS;
  title: string;
  description: string;
}

/**
 * Marketing panel of the register screen: value proposition and capabilities.
 *
 * It is hidden below `lg`, so the form is what a phone shows first.
 */
@Component({
  selector: 'app-register-hero',
  imports: [NgIcon],
  templateUrl: './register-hero.html',
  viewProviders: [
    provideIcons({
      matPrecisionManufacturingOutline,
      matArchitectureOutline,
      matEcoOutline,
      matValveOutline,
      matSummarizeOutline,
    }),
  ],
  host: {
    class:
      'hidden lg:flex lg:w-5/12 bg-primary text-on-primary p-space-lg lg:p-space-xl flex-col justify-between relative overflow-hidden',
  },
})
export class RegisterHero {
  /** Registry keys, so the template can resolve `feature.icon` without a global registry. */
  protected readonly featureIcons = FEATURE_ICONS;

  protected readonly features: readonly HeroFeature[] = [
    {
      icon: 'architecture',
      title: 'Diseño geométrico 2D interactivo',
      description:
        'Cotas dinámicas en tiempo real, delimitación poligonal de parcelas y visualización de curvas de nivel.',
    },
    {
      icon: 'eco',
      title: 'Reparto inteligente y balance hídrico',
      description:
        'Zonificación según Kc de cultivo, tipo de suelo y evapotranspiración de referencia local.',
    },
    {
      icon: 'valve',
      title: 'Dimensionamiento de red, bombas y tuberías',
      description:
        'Cálculo de caídas de presión, caudal de goteros autocompensantes y sectorización automática de electroválvulas.',
    },
    {
      icon: 'summarize',
      title: 'Cómputo de materiales y planos PDF',
      description:
        'Listados cuantitativos para presupuestos instantáneos y planos de replanteo a escala.',
    },
  ];
}
