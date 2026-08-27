declare namespace JSX {
  interface Element {}
  interface IntrinsicAttributes { key?: string | number }
  interface IntrinsicElements { [elemName: string]: any }
}

declare namespace React {
  type ReactNode = any;
  type ComponentType<P = any> = (props: P) => JSX.Element | null;
}

declare module 'react' {
  export as namespace React;
  export type ReactNode = React.ReactNode;
  export type ComponentType<P = any> = React.ComponentType<P>;
  export interface SyntheticEvent<T = any> { preventDefault(): void; currentTarget: T; target: T }
  export interface FormEvent<T = any> extends SyntheticEvent<T> {}
  export interface ChangeEvent<T = any> extends SyntheticEvent<T> {}
  export interface KeyboardEvent<T = any> extends SyntheticEvent<T> { key: string; shiftKey: boolean }
  export function useState<T>(initial: T): [T, (value: T | ((previous: T) => T)) => void];
  export function useState<T = undefined>(): [T | undefined, (value: T | undefined | ((previous: T | undefined) => T | undefined)) => void];
  export function useEffect(effect: () => void | (() => void), deps?: readonly unknown[]): void;
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: readonly unknown[]): T;
  const React: {
    Fragment: any;
  };
  export default React;
}

declare module 'react/jsx-runtime' {
  export const Fragment: any;
  export function jsx(type: any, props: any, key?: any): JSX.Element;
  export function jsxs(type: any, props: any, key?: any): JSX.Element;
}
