import { Component, Suspense, type ReactNode } from "react";

type Props = { children: ReactNode; onClose: () => void };

/** A failed optional chunk cannot unmount the chart or discard its draft state. */
export default class DeferredPanel extends Component<
  Props,
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <div role="alert">
          Panel yüklenemedi. Sayfayı yenileyip tekrar deneyin.
          <button onClick={this.props.onClose}>Kapat</button>
        </div>
      );
    return (
      <Suspense
        fallback={
          <div role="status">
            Panel yükleniyor…
            <button onClick={this.props.onClose}>Vazgeç</button>
          </div>
        }
      >
        {this.props.children}
      </Suspense>
    );
  }
}
