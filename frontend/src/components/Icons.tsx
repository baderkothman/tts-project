import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

const common = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
};

export function WaveIcon(props: IconProps) {
  return (
    <svg {...common} {...props}>
      <path d="M3 12h2l2-7 3 14 3-11 2 8 2-4h4" />
    </svg>
  );
}

export function PlayIcon(props: IconProps) {
  return (
    <svg {...common} {...props}>
      <path d="m8 5 11 7-11 7V5Z" />
    </svg>
  );
}

export function EyeIcon(props: IconProps) {
  return (
    <svg {...common} {...props}>
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

export function CompareIcon(props: IconProps) {
  return (
    <svg {...common} {...props}>
      <path d="M8 3 4 7l4 4M4 7h13M16 21l4-4-4-4m4 4H7" />
    </svg>
  );
}

export function SparkIcon(props: IconProps) {
  return (
    <svg {...common} {...props}>
      <path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3Z" />
      <path d="m18.5 14 .7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z" />
    </svg>
  );
}
