import { Component } from '@angular/core';

interface HeroFeature {
  icon: string;
  title: string;
  description: string;
}

/** Marketing panel of the register screen: value proposition and capabilities. */
@Component({
  selector: 'app-register-hero',
  templateUrl: './register-hero.html',
  host: {
    class:
      'lg:w-5/12 bg-primary text-on-primary p-space-lg lg:p-space-xl flex flex-col justify-between relative overflow-hidden',
  },
})
export class RegisterHero {
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
