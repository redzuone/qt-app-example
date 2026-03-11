/**
 * Style Selector Control for MapLibre GL
 * Provides a collapsible panel with radio-button style options.
 */

export class StyleSelectorControl {
    constructor(styleOptions, defaultStyleKey, onStyleChange) {
        this.styleOptions = styleOptions;
        this.defaultStyleKey = defaultStyleKey;
        this.onStyleChange = onStyleChange;
        this._map = null;
        this._container = null;
        this._panel = null;
        this._button = null;
    }

    onAdd(mapInstance) {
        this._map = mapInstance;
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl maplibregl-ctrl-group';
        this._container.style.display = 'flex';
        this._container.style.flexDirection = 'column';

        // Toggle button
        this._button = document.createElement('button');
        this._button.className = 'maplibregl-ctrl-icon';
        this._button.title = 'Map style';
        this._button.setAttribute('aria-label', 'Map style');
        const img = document.createElement('img');
        img.src = '/img/map.svg';
        img.style.width = '16px';
        img.style.height = '16px';
        this._button.appendChild(img);
        this._button.style.cursor = 'pointer';
        this._button.style.display = 'flex';
        this._button.style.alignItems = 'center';
        this._button.style.justifyContent = 'center';
        this._button.addEventListener('click', () => this._togglePanel());
        this._container.appendChild(this._button);

        // Radio list panel
        this._panel = document.createElement('div');
        this._panel.style.display = 'none';
        this._panel.style.background = '#fff';
        this._panel.style.padding = '10px';
        this._panel.style.borderRadius = '4px';
        this._panel.style.marginTop = '5px';
        this._panel.style.minWidth = '140px';
        this._panel.style.fontSize = '12px';
        this._panel.style.boxShadow = '0 0 0 2px rgba(0,0,0,0.1)';

        Object.entries(this.styleOptions).forEach(([key, option]) => {
            const label = document.createElement('label');
            label.style.display = 'flex';
            label.style.alignItems = 'center';
            label.style.marginBottom = '8px';
            label.style.cursor = 'pointer';

            const radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'map-style';
            radio.value = key;
            radio.checked = key === this.defaultStyleKey;
            radio.addEventListener('change', (e) => this._onChange(e));
            radio.style.marginRight = '6px';

            const text = document.createElement('span');
            text.textContent = option.label;

            label.appendChild(radio);
            label.appendChild(text);
            this._panel.appendChild(label);
        });

        this._container.appendChild(this._panel);
        return this._container;
    }

    onRemove() {
        if (this._container && this._container.parentNode) {
            this._container.parentNode.removeChild(this._container);
        }
        this._map = undefined;
    }

    _togglePanel() {
        this._panel.style.display = this._panel.style.display === 'none' ? 'block' : 'none';
    }

    _onChange(event) {
        if (event.target.checked && this.onStyleChange) {
            this.onStyleChange(event.target.value);
            this._togglePanel();
        }
    }
}
