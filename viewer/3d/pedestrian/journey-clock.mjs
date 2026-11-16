export const CLOCK_ORIGIN=8*3600+50*60;
export function clockTime(seconds){const n=Math.round(CLOCK_ORIGIN+seconds);return [Math.floor(n/3600),Math.floor(n%3600/60),n%60].map(v=>String(v).padStart(2,'0')).join(':');}
export function modelTime(value){if(!/^\d{2}:\d{2}(:\d{2})?$/.test(value))return NaN;const [h,m,s=0]=value.split(':').map(Number);if(h>23||m>59||s>59)return NaN;return h*3600+m*60+s-CLOCK_ORIGIN;}
