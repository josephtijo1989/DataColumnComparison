document.addEventListener('DOMContentLoaded', () => {
    // DOM Element references for Source 1
    const src1Type = document.getElementById('src1_type');
    const src1Schema = document.getElementById('src1_schema');
    const src1Table = document.getElementById('src1_table');
    const src1Column = document.getElementById('src1_column');

    // DOM Element references for Source 2
    const src2Type = document.getElementById('src2_type');
    const src2Schema = document.getElementById('src2_schema');
    const src2Table = document.getElementById('src2_table');
    const src2Column = document.getElementById('src2_column');

    // Dynamic Label references
    const lblSrc1Unique = document.getElementById('lbl_src1_unique');
    const lblSrc2Unique = document.getElementById('lbl_src2_unique');
    const lblOnlySrc1 = document.getElementById('lbl_only_src1');
    const lblOnlySrc2 = document.getElementById('lbl_only_src2');

    // Compare button and Results
    const compareBtn = document.getElementById('compare_btn');
    const resSrc1Count = document.getElementById('res_src1_count');
    const resSrc2Count = document.getElementById('res_src2_count');
    const resMatchingVal = document.getElementById('res_matching_val');
    const resMatchingPct = document.getElementById('res_matching_pct');
    const resOnlySrc1 = document.getElementById('res_only_src1');
    const resOnlySrc2 = document.getElementById('res_only_src2');

    // Function to dynamically update table labels with selected Table Name (Source Type)
    function updateDynamicLabels() {
        const s1Type = src1Type.value || 'Databricks';
        const s1TableVal = src1Table.value;
        const s1Table = s1TableVal && !s1TableVal.startsWith('Select') && !s1TableVal.startsWith('Loading') ? s1TableVal : '';
        const s1Tag = s1Table ? `${s1Table} (${s1Type})` : s1Type;

        const s2Type = src2Type.value || 'SQL Server';
        const s2TableVal = src2Table.value;
        const s2Table = s2TableVal && !s2TableVal.startsWith('Select') && !s2TableVal.startsWith('Loading') ? s2TableVal : '';
        const s2Tag = s2Table ? `${s2Table} (${s2Type})` : s2Type;

        lblSrc1Unique.textContent = `${s1Tag} Unique Records`;
        lblSrc2Unique.textContent = `${s2Tag} Unique Records`;
        lblOnlySrc1.textContent = `Only In ${s1Tag}`;
        lblOnlySrc2.textContent = `Only In ${s2Tag}`;
    }

    // Class to turn standard select into a searchable select
    class SearchableSelect {
        constructor(selectElem) {
            this.selectElem = selectElem;
            this.wrapper = document.createElement('div');
            this.wrapper.className = 'custom-select-wrapper';

            this.trigger = document.createElement('div');
            this.trigger.className = 'custom-select-trigger';
            this.triggerText = document.createElement('span');
            this.triggerText.textContent = selectElem.options[selectElem.selectedIndex]?.text || 'Select...';
            this.arrow = document.createElement('span');
            this.arrow.className = 'arrow-icon';
            this.arrow.textContent = '▼';

            this.trigger.appendChild(this.triggerText);
            this.trigger.appendChild(this.arrow);

            this.panel = document.createElement('div');
            this.panel.className = 'custom-dropdown-panel';

            this.searchBox = document.createElement('div');
            this.searchBox.className = 'search-input-box';
            this.searchInput = document.createElement('input');
            this.searchInput.type = 'text';
            this.searchInput.placeholder = '🔍 Search option...';

            this.searchBox.appendChild(this.searchInput);

            this.optionsList = document.createElement('div');
            this.optionsList.className = 'options-list';

            this.panel.appendChild(this.searchBox);
            this.panel.appendChild(this.optionsList);

            this.wrapper.appendChild(this.trigger);
            this.wrapper.appendChild(this.panel);

            // Hide original select
            this.selectElem.style.display = 'none';
            this.selectElem.parentNode.insertBefore(this.wrapper, this.selectElem);

            this.initEvents();
            this.syncWithOptions();
        }

        initEvents() {
            this.trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.selectElem.disabled) return;
                closeAllSearchableDropdowns(this);
                this.wrapper.classList.toggle('open');
                if (this.wrapper.classList.contains('open')) {
                    this.searchInput.value = '';
                    this.filterOptions('');
                    this.searchInput.focus();
                }
            });

            this.searchInput.addEventListener('click', (e) => e.stopPropagation());

            this.searchInput.addEventListener('input', (e) => {
                this.filterOptions(e.target.value);
            });

            // Listen for mutations on original select to auto re-sync
            const observer = new MutationObserver(() => this.syncWithOptions());
            observer.observe(this.selectElem, { childList: true, attributes: true });
        }

        syncWithOptions() {
            if (this.selectElem.disabled) {
                this.trigger.classList.add('disabled');
            } else {
                this.trigger.classList.remove('disabled');
            }

            const selectedOpt = this.selectElem.options[this.selectElem.selectedIndex];
            this.triggerText.textContent = selectedOpt ? selectedOpt.text : 'Select...';

            this.optionsList.innerHTML = '';
            const opts = Array.from(this.selectElem.options);

            if (opts.length === 0 || (opts.length === 1 && !opts[0].value)) {
                const noOpt = document.createElement('div');
                noOpt.className = 'no-options';
                noOpt.textContent = opts[0] ? opts[0].text : 'No options available';
                this.optionsList.appendChild(noOpt);
                return;
            }

            opts.forEach(opt => {
                if (!opt.value && opt.text.startsWith('Select')) return; // Skip default placeholder in list
                const item = document.createElement('div');
                item.className = 'option-item';
                if (opt.selected) item.classList.add('selected');
                item.textContent = opt.text;
                item.dataset.value = opt.value;

                item.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.selectElem.value = opt.value;
                    this.triggerText.textContent = opt.text;
                    this.wrapper.classList.remove('open');
                    this.selectElem.dispatchEvent(new Event('change'));
                });

                this.optionsList.appendChild(item);
            });
        }

        filterOptions(query) {
            const term = query.toLowerCase().trim();
            const items = this.optionsList.querySelectorAll('.option-item');
            let hasVisible = false;

            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(term)) {
                    item.style.display = 'block';
                    hasVisible = true;
                } else {
                    item.style.display = 'none';
                }
            });

            let noMatchMsg = this.optionsList.querySelector('.no-options');
            if (!hasVisible) {
                if (!noMatchMsg) {
                    noMatchMsg = document.createElement('div');
                    noMatchMsg.className = 'no-options';
                    this.optionsList.appendChild(noMatchMsg);
                }
                noMatchMsg.textContent = `No match for "${query}"`;
            } else if (noMatchMsg) {
                noMatchMsg.remove();
            }
        }
    }

    const allDropdownInstances = [];
    function closeAllSearchableDropdowns(exceptInstance) {
        allDropdownInstances.forEach(inst => {
            if (inst !== exceptInstance) {
                inst.wrapper.classList.remove('open');
            }
        });
    }

    document.addEventListener('click', () => closeAllSearchableDropdowns(null));

    // Convert dropdowns to Searchable Selects
    allDropdownInstances.push(new SearchableSelect(src1Type));
    allDropdownInstances.push(new SearchableSelect(src1Schema));
    allDropdownInstances.push(new SearchableSelect(src1Table));
    allDropdownInstances.push(new SearchableSelect(src1Column));

    allDropdownInstances.push(new SearchableSelect(src2Type));
    allDropdownInstances.push(new SearchableSelect(src2Schema));
    allDropdownInstances.push(new SearchableSelect(src2Table));
    allDropdownInstances.push(new SearchableSelect(src2Column));

    // Initialize Schemas on startup
    loadSchemas(1);
    loadSchemas(2);
    updateDynamicLabels();

    // Helper to clear existing comparison results
    function clearResults() {
        resSrc1Count.textContent = '0';
        resSrc2Count.textContent = '0';
        resMatchingVal.textContent = '0';
        resMatchingPct.textContent = '0.00%';
        resOnlySrc1.textContent = '0';
        resOnlySrc2.textContent = '0';
    }

    // Event listeners Source 1
    src1Type.addEventListener('change', () => {
        clearResults();
        resetDropdown(src1Table, 'Select Table...');
        resetDropdown(src1Column, 'Select Column...');
        loadSchemas(1);
        updateDynamicLabels();
    });

    src1Schema.addEventListener('change', () => {
        clearResults();
        resetDropdown(src1Table, 'Select Table...');
        resetDropdown(src1Column, 'Select Column...');
        if (src1Schema.value) loadTables(1);
        updateDynamicLabels();
    });

    src1Table.addEventListener('change', () => {
        clearResults();
        resetDropdown(src1Column, 'Select Column...');
        if (src1Table.value) loadColumns(1);
        updateDynamicLabels();
    });

    src1Column.addEventListener('change', () => {
        clearResults();
        checkCompareReady();
        updateDynamicLabels();
    });

    // Event listeners Source 2
    src2Type.addEventListener('change', () => {
        clearResults();
        resetDropdown(src2Table, 'Select Table...');
        resetDropdown(src2Column, 'Select Column...');
        loadSchemas(2);
        updateDynamicLabels();
    });

    src2Schema.addEventListener('change', () => {
        clearResults();
        resetDropdown(src2Table, 'Select Table...');
        resetDropdown(src2Column, 'Select Column...');
        if (src2Schema.value) loadTables(2);
        updateDynamicLabels();
    });

    src2Table.addEventListener('change', () => {
        clearResults();
        resetDropdown(src2Column, 'Select Column...');
        if (src2Table.value) loadColumns(2);
        updateDynamicLabels();
    });

    src2Column.addEventListener('change', () => {
        clearResults();
        checkCompareReady();
        updateDynamicLabels();
    });

    // Compare button click event
    compareBtn.addEventListener('click', performComparison);

    function resetDropdown(selectElem, placeholder) {
        selectElem.innerHTML = `<option value="">${placeholder}</option>`;
        selectElem.disabled = true;
        checkCompareReady();
    }

    async function loadSchemas(sourceNum) {
        const typeElem = sourceNum === 1 ? src1Type : src2Type;
        const schemaElem = sourceNum === 1 ? src1Schema : src2Schema;
        const sourceType = typeElem.value;

        schemaElem.innerHTML = '<option value="">Loading Schemas...</option>';
        schemaElem.disabled = true;

        try {
            const resp = await fetch(`/api/schemas?source_type=${encodeURIComponent(sourceType)}`);
            const data = await resp.json();
            schemaElem.innerHTML = '<option value="">Select Schema...</option>';
            data.schemas.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.textContent = s;
                schemaElem.appendChild(opt);
            });
            schemaElem.disabled = false;
        } catch (err) {
            schemaElem.innerHTML = '<option value="">Failed to load schemas</option>';
            console.error(err);
        }
    }

    async function loadTables(sourceNum) {
        const typeElem = sourceNum === 1 ? src1Type : src2Type;
        const schemaElem = sourceNum === 1 ? src1Schema : src2Schema;
        const tableElem = sourceNum === 1 ? src1Table : src2Table;

        tableElem.innerHTML = '<option value="">Loading Tables...</option>';
        tableElem.disabled = true;

        try {
            const resp = await fetch(`/api/tables?source_type=${encodeURIComponent(typeElem.value)}&schema=${encodeURIComponent(schemaElem.value)}`);
            const data = await resp.json();
            tableElem.innerHTML = '<option value="">Select Table...</option>';
            data.tables.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                tableElem.appendChild(opt);
            });
            tableElem.disabled = false;
        } catch (err) {
            tableElem.innerHTML = '<option value="">Failed to load tables</option>';
            console.error(err);
        }
    }

    async function loadColumns(sourceNum) {
        const typeElem = sourceNum === 1 ? src1Type : src2Type;
        const schemaElem = sourceNum === 1 ? src1Schema : src2Schema;
        const tableElem = sourceNum === 1 ? src1Table : src2Table;
        const columnElem = sourceNum === 1 ? src1Column : src2Column;

        columnElem.innerHTML = '<option value="">Loading Columns...</option>';
        columnElem.disabled = true;

        try {
            const resp = await fetch(`/api/columns?source_type=${encodeURIComponent(typeElem.value)}&schema=${encodeURIComponent(schemaElem.value)}&table=${encodeURIComponent(tableElem.value)}`);
            const data = await resp.json();
            columnElem.innerHTML = '<option value="">Select Column...</option>';
            data.columns.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = c;
                columnElem.appendChild(opt);
            });
            columnElem.disabled = false;
        } catch (err) {
            columnElem.innerHTML = '<option value="">Failed to load columns</option>';
            console.error(err);
        }
    }

    function checkCompareReady() {
        if (src1Column.value && src2Column.value) {
            compareBtn.disabled = false;
        } else {
            compareBtn.disabled = true;
        }
    }

    async function performComparison() {
        clearResults();
        updateDynamicLabels();
        compareBtn.disabled = true;
        compareBtn.textContent = 'Comparing...';

        const payload = {
            source1: {
                type: src1Type.value,
                schema: src1Schema.value,
                table: src1Table.value,
                column: src1Column.value
            },
            source2: {
                type: src2Type.value,
                schema: src2Schema.value,
                table: src2Table.value,
                column: src2Column.value
            }
        };

        try {
            const resp = await fetch('/api/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await resp.json();

            // Update UI Table Results
            resSrc1Count.textContent = result.source1_count.toLocaleString();
            resSrc2Count.textContent = result.source2_count.toLocaleString();
            resMatchingVal.textContent = result.matching_count.toLocaleString();

            if (result.matching_percentage !== undefined) {
                resMatchingPct.textContent = `${Number(result.matching_percentage).toFixed(2)}%`;
            } else {
                resMatchingPct.textContent = '0.00%';
            }

            resOnlySrc1.textContent = result.only_source1.toLocaleString();
            resOnlySrc2.textContent = result.only_source2.toLocaleString();

        } catch (err) {
            alert('Error running comparison: ' + err.message);
            console.error(err);
        } finally {
            compareBtn.disabled = false;
            compareBtn.textContent = 'Compare Data';
        }
    }
});
