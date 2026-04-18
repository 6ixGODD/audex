/**
 * Audex Overlay Input
 *
 * 触发方式：用户双击任意带有 audex-oi-* 标记类的 Quasar q-field 元素（或其子节点）。
 * 检测策略：document 级 capture-phase 委托，走 composedPath 向上找标记类。
 *   不依赖 MutationObserver，避免 Vue 响应式绑定 class 的时序问题。
 *
 * 标记类（由 Python 组件写入 Quasar 根元素）：
 *   audex-oi-never  – 永不唤起
 *   audex-oi-always – 双击必唤起
 *   audex-oi-auto   – 智能检测（无物理键盘则唤起）
 */
(function () {
    'use strict';

    if (window._audexOverlayInputLoaded) return;
    window._audexOverlayInputLoaded = true;

    /* ── 物理键盘检测 ──────────────────────────────────────────────── */
    var _lastKeyMs = 0;
    var KB_WINDOW = 60000; // 60 s 内有键盘事件则认为键盘在线

    document.addEventListener('keydown', function (e) {
        if (e.isTrusted !== false) _lastKeyMs = Date.now();
    }, true);

    function _hasPhysicalKeyboard() {
        if (Date.now() - _lastKeyMs < KB_WINDOW) return true;
        // 触摸屏且无精确指针 → 平板/手机，无外接键盘
        var coarse = window.matchMedia('(pointer: coarse)').matches;
        var fine   = window.matchMedia('(any-pointer: fine)').matches;
        return !(coarse && !fine);
    }

    function _shouldShow(mode) {
        if (mode === 'never')  return false;
        if (mode === 'always') return true;
        return !_hasPhysicalKeyboard(); // auto
    }

    /* ── 从事件路径中找标记元素 ──────────────────────────────────── */
    var MARKERS = ['audex-oi-always', 'audex-oi-auto', 'audex-oi-never'];

    function _findMarker(e) {
        var path = (e.composedPath && e.composedPath()) || [];
        // composedPath 包含 Shadow DOM 内部节点，直接扫最可靠
        for (var i = 0; i < path.length; i++) {
            var n = path[i];
            if (n.classList) {
                for (var j = 0; j < MARKERS.length; j++) {
                    if (n.classList.contains(MARKERS[j])) return n;
                }
            }
        }
        // 降级：手动向上遍历
        var el = e.target;
        while (el && el !== document.documentElement) {
            if (el.classList) {
                for (var k = 0; k < MARKERS.length; k++) {
                    if (el.classList.contains(MARKERS[k])) return el;
                }
            }
            el = el.parentElement;
        }
        return null;
    }

    function _getMode(el) {
        if (el.classList.contains('audex-oi-always')) return 'always';
        if (el.classList.contains('audex-oi-auto'))   return 'auto';
        return 'never';
    }

    /* ── 遮罩逻辑 ────────────────────────────────────────────────── */
    var _active = null;

    function _syncBack(qFieldEl, value) {
        var native = qFieldEl.querySelector('textarea') || qFieldEl.querySelector('input');
        if (!native) return;
        var proto = Object.getOwnPropertyDescriptor(
            native.tagName === 'TEXTAREA'
                ? window.HTMLTextAreaElement.prototype
                : window.HTMLInputElement.prototype,
            'value'
        );
        if (proto && proto.set) proto.set.call(native, value);
        else native.value = value;
        native.dispatchEvent(new Event('input',  { bubbles: true }));
        native.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function _readNative(qFieldEl) {
        var n = qFieldEl.querySelector('textarea') || qFieldEl.querySelector('input');
        return n ? n.value : '';
    }

    function _show(qFieldEl) {
        if (_active) _hide();

        var native  = qFieldEl.querySelector('textarea') || qFieldEl.querySelector('input');
        var isTA    = native && native.tagName === 'TEXTAREA';
        var isPwd   = native && native.type === 'password';
        var ph      = (native && native.placeholder) || '';
        var initVal = _readNative(qFieldEl);

        var backdrop = document.createElement('div');
        backdrop.className = 'audex-oi-backdrop';

        var bar = document.createElement('div');
        bar.className = 'audex-oi-bar' + (isTA ? ' audex-oi-bar--ta' : '');

        var field = document.createElement(isTA ? 'textarea' : 'input');
        field.className = 'audex-oi-field' + (isTA ? ' audex-oi-textarea' : '');
        if (!isTA) field.type = isPwd ? 'password' : 'text';
        field.placeholder = ph;
        field.value = initVal;
        // Linux平板输入法需要这些属性来识别可输入元素
        field.setAttribute('inputmode', isPwd ? 'text' : 'text');
        field.setAttribute('autocomplete', 'off');
        field.setAttribute('autocapitalize', 'off');

        var btn = document.createElement('button');
        btn.className = 'audex-oi-confirm';
        btn.setAttribute('aria-label', '确认');

        function confirm() {
            _syncBack(qFieldEl, field.value);
            _hide();
        }

        btn.addEventListener('click', confirm);

        /* Clicks on the backdrop (outside the bar) confirm and close.
           Use preventDefault so the mousedown doesn't move focus away
           from the bar before confirm() runs. */
        backdrop.addEventListener('mousedown', function (ev) {
            if (!bar.contains(ev.target)) {
                ev.preventDefault();
                confirm();
            }
        });

        field.addEventListener('keydown', function (ev) {
            if (ev.key === 'Escape') { _hide(); return; }
            if (ev.key === 'Enter' && (!isTA || ev.ctrlKey)) confirm();
        });

        bar.appendChild(field);
        bar.appendChild(btn);
        backdrop.appendChild(bar);

        /* Always append to body so position:fixed covers the full viewport.
           Quasar's focus-trap is neutralised by the focusin bubble interceptor below. */
        document.body.appendChild(backdrop);
        _active = backdrop;

        /* Stop focus-trap libraries (Quasar dialog, etc.) from seeing
           focusin events that originate inside our overlay.
           Registered on the backdrop itself – fires before any ancestor. */
        backdrop.addEventListener('focusin', function (ev) {
            ev.stopImmediatePropagation();
        }, true);

        function _focusField() {
            if (!_active) return;
            // Linux平板输入法需要先触发一次blur再focus来强制唤起
            field.blur();
            setTimeout(function() {
                field.focus();
                // 触发一次click事件来激活输入法上下文
                field.click();
                if (!isTA) {
                    try { field.setSelectionRange(field.value.length, field.value.length); } catch (_) {}
                }
            }, 10);
        }

        /* Try to focus immediately, on next frame, and after multiple delays
           to ensure the DOM is fully rendered and the input method daemon recognizes it. */
        _focusField();
        requestAnimationFrame(_focusField);
        setTimeout(_focusField, 80);
        setTimeout(_focusField, 200);  // 额外延迟确保输入法守护进程响应
    }

    function _hide() {
        if (_active) { _active.remove(); _active = null; }
    }

    /* ── 公开 API（供 Python 端通过 run_javascript 调用） ────────── */
    window.AudexOverlayInput = {
        /**
         * 直接按元素 ID 触发遮罩（Python 端 on("dblclick") 回调调用）
         * elId: NiceGUI 渲染时的 DOM id，格式为 "c{element.id}"
         * mode: 'never' | 'always' | 'auto'
         */
        triggerById: function (elId, mode) {
            if (!_shouldShow(mode)) return;
            var el = document.getElementById(elId);
            if (!el) return;
            _show(el);
        }
    };

    /* ── focusin 拦截：阻止 document 级 focus trap（如 Quasar dialog）抢走焦点 ── */
    /* Fires in bubble phase at body – after the element receives focus but
       before document-level bubble listeners (where Quasar's trap lives). */
    document.body.addEventListener('focusin', function (e) {
        if (_active && _active.contains(e.target)) {
            e.stopPropagation();
        }
    });

    /* ── document 级委托（capture 阶段，Vue class 时序无关） ──────── */
    document.addEventListener('dblclick', function (e) {
        var marker = _findMarker(e);
        if (!marker) return;
        var mode = _getMode(marker);
        if (!_shouldShow(mode)) return;
        e.preventDefault();
        e.stopPropagation();
        _show(marker);
    }, true); // capture = true：在任何子节点处理器之前拦截

})();
