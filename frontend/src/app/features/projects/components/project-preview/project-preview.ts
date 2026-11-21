import { Component, computed, input } from '@angular/core';
import { Project } from '../../models/project.model';
import { cropPercent, formatThousands } from '../../utils/project-format';

interface PreviewBlock {
  name: string;
  color: string;
  x: number;
  width: number;
  areaLabel: string;
}

const MARGIN_X = 24;
const INNER_WIDTH = 312;
const INNER_HEIGHT = 84;
const INNER_TOP = 30;

/**
 * Schematic preview generated from the project's crops, so every card shares
 * one renderer instead of a hand-drawn SVG per project.
 */
@Component({
  selector: 'app-project-preview',
  template: `
    <svg
      class="w-full h-auto"
      viewBox="0 0 360 150"
      role="img"
      [attr.aria-label]="'Plano esquemático de ' + project().name"
    >
      @if (project().parcelShape === 'trapezoid') {
        <polygon
          [attr.points]="trapezoidPoints"
          fill="#cfa98a"
          stroke="#707a6f"
          stroke-width="1.5"
        />
      } @else {
        @for (block of blocks(); track block.name) {
          <rect
            [attr.x]="block.x"
            [attr.y]="INNER_TOP"
            [attr.width]="block.width"
            [attr.height]="INNER_HEIGHT"
            [attr.fill]="block.color"
            stroke="#ffffff"
            stroke-width="1"
          />
        }
      }

      <!-- Drip laterals -->
      @for (line of dripLines(); track line) {
        <line
          [attr.x1]="MARGIN_X + 6"
          [attr.y1]="line"
          [attr.x2]="MARGIN_X + INNER_WIDTH - 6"
          [attr.y2]="line"
          stroke="#1f6c3a"
          stroke-width="0.8"
          stroke-dasharray="3 2"
          opacity="0.55"
        />
      }

      <!-- Main pipe and water source -->
      <polyline
        [attr.points]="mainPipe"
        fill="none"
        stroke="#3b6fd4"
        stroke-width="2.5"
        stroke-linejoin="round"
      />
      <circle cx="14" cy="42" r="5" fill="#ffffff" stroke="#3b6fd4" stroke-width="2.5" />

      <rect
        [attr.x]="MARGIN_X"
        [attr.y]="INNER_TOP"
        [attr.width]="INNER_WIDTH"
        [attr.height]="INNER_HEIGHT"
        fill="none"
        stroke="#404940"
        stroke-width="1.5"
      />

      @for (block of blocks(); track block.name) {
        <text
          [attr.x]="block.x + block.width / 2"
          [attr.y]="INNER_TOP + INNER_HEIGHT / 2 - 3"
          text-anchor="middle"
          font-size="9"
          font-weight="600"
          fill="#00210d"
        >
          {{ block.name }}
        </text>
        <text
          [attr.x]="block.x + block.width / 2"
          [attr.y]="INNER_TOP + INNER_HEIGHT / 2 + 9"
          text-anchor="middle"
          font-size="7.5"
          fill="#404940"
        >
          {{ block.areaLabel }}
        </text>
      }

      @if (project().parcelShape === 'trapezoid') {
        <text x="180" y="76" text-anchor="middle" font-size="9" font-weight="600" fill="#00210d">
          {{ trapezoidLabel() }}
        </text>
      }
    </svg>
  `,
})
export class ProjectPreview {
  readonly project = input.required<Project>();

  protected readonly MARGIN_X = MARGIN_X;
  protected readonly INNER_WIDTH = INNER_WIDTH;
  protected readonly INNER_HEIGHT = INNER_HEIGHT;
  protected readonly INNER_TOP = INNER_TOP;

  protected readonly trapezoidPoints = '24,114 96,30 336,30 336,114';
  protected readonly mainPipe = '14,42 14,126 336,126';

  protected readonly blocks = computed<PreviewBlock[]>(() => {
    const project = this.project();
    const total = project.crops.reduce((sum, crop) => sum + crop.areaM2, 0) || 1;

    let cursor = 0;
    return project.crops.map((crop) => {
      const width = (crop.areaM2 / total) * INNER_WIDTH;
      const block: PreviewBlock = {
        name: crop.name,
        color: crop.color,
        x: MARGIN_X + cursor,
        width,
        areaLabel: `${formatThousands(crop.areaM2)} m² (${cropPercent(crop.areaM2, total)}%)`,
      };
      cursor += width;
      return block;
    });
  });

  protected readonly dripLines = computed(() => {
    const lines: number[] = [];
    const step = INNER_HEIGHT / 5;
    for (let index = 1; index < 5; index++) {
      lines.push(INNER_TOP + step * index);
    }
    return lines;
  });

  protected readonly trapezoidLabel = computed(() => {
    const crop = this.project().crops[0];
    return crop ? `${crop.name} · ${formatThousands(crop.areaM2)} m²` : '';
  });
}
