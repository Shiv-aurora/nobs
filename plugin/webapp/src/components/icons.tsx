import React from 'react';

interface IconProps {
    size?: number;
}

const base = (size: number) => ({width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const});

export const SparkIcon = ({size = 20}: IconProps) => <svg {...base(size)}><path d='m12 3 1.3 4.2L17 9l-3.7 1.8L12 15l-1.3-4.2L7 9l3.7-1.8L12 3Z'/><path d='m18 15 .7 2.3L21 18l-2.3.7L18 21l-.7-2.3L15 18l2.3-.7L18 15Z'/></svg>;
export const HomeIcon = ({size = 19}: IconProps) => <svg {...base(size)}><path d='m3 11 9-8 9 8'/><path d='M5 10v10h14V10'/><path d='M9 20v-6h6v6'/></svg>;
export const InboxIcon = ({size = 19}: IconProps) => <svg {...base(size)}><path d='M4 4h16v13H4z'/><path d='m4 13 4-3 3 3h2l3-3 4 3'/><path d='M8 20h8'/></svg>;
export const ProjectIcon = ({size = 19}: IconProps) => <svg {...base(size)}><rect x='3' y='4' width='18' height='16' rx='3'/><path d='M8 4v16M8 9h13'/></svg>;
export const PeopleIcon = ({size = 19}: IconProps) => <svg {...base(size)}><circle cx='9' cy='8' r='3'/><path d='M3 20c0-4 2-7 6-7s6 3 6 7'/><circle cx='17' cy='9' r='2'/><path d='M16 14c3 0 5 2 5 5'/></svg>;
export const NetworkIcon = ({size = 19}: IconProps) => <svg {...base(size)}><circle cx='12' cy='5' r='3'/><circle cx='5' cy='18' r='3'/><circle cx='19' cy='18' r='3'/><path d='m10.5 7.5-4 7M13.5 7.5l4 7M8 18h8'/></svg>;
export const AuditIcon = ({size = 19}: IconProps) => <svg {...base(size)}><path d='M6 3h12v18H6z'/><path d='M9 8h6M9 12h6M9 16h4'/></svg>;
export const RoomIcon = ({size = 19}: IconProps) => <svg {...base(size)}><path d='M4 4h16v13H8l-4 4V4Z'/></svg>;
export const SearchIcon = ({size = 21}: IconProps) => <svg {...base(size)}><circle cx='11' cy='11' r='7'/><path d='m16.5 16.5 4 4'/></svg>;
export const ArrowIcon = ({size = 18}: IconProps) => <svg {...base(size)}><path d='M5 12h14M14 7l5 5-5 5'/></svg>;
export const ShieldIcon = ({size = 18}: IconProps) => <svg {...base(size)}><path d='M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6l-7-3Z'/><path d='m9 12 2 2 4-5'/></svg>;
export const CheckIcon = ({size = 18}: IconProps) => <svg {...base(size)}><path d='m5 12 4 4L19 6'/></svg>;
export const ClockIcon = ({size = 18}: IconProps) => <svg {...base(size)}><circle cx='12' cy='12' r='9'/><path d='M12 7v5l3 2'/></svg>;
export const ExternalIcon = ({size = 15}: IconProps) => <svg {...base(size)}><path d='M14 4h6v6M20 4l-9 9'/><path d='M18 13v7H4V6h7'/></svg>;
export const ResetIcon = ({size = 17}: IconProps) => <svg {...base(size)}><path d='M4 12a8 8 0 1 0 2-5.3L4 9'/><path d='M4 4v5h5'/></svg>;
