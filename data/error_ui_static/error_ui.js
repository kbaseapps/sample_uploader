window.errorUI = (()=>{
  // Convert from index to excel-style column string
  const indexToLetters = (index) => {
    let str = "";
    const aCode = 'A'.charCodeAt(0);
    let rem = index;
    while (rem >= 0) {
        str = String.fromCharCode(rem % 26 + aCode) + str;
        rem = Math.floor(rem / 26) - 1;
    }
    return str;
  }

  // Convert from excel-style column string to index
  const lettersToIndex = (str) => {
    const lttrs = [...str.toUpperCase()];
    const aCode = 'A'.charCodeAt(0);
    let index = 0;
    let p = 1;
    while (lttrs.length>0){
      index += p * (lttrs.pop().charCodeAt(0)+1 - aCode)
      p = p * 26;
    }
    return index-1;
  }

  // Runs an action for each location containing `indexes`
  // (cell, row, col)
  const forEachLocation = (indexes, sampleTable, action) => {
    const dataCells = indexes.filter(i=>i.column!==0);
    dataCells.forEach(selCell=>{
      const col = indexToLetters(selCell.column-1);
      const row = sampleTable.row(selCell.row).data()[0];
      action(col)
      action(row)
      action(`${col}${row}`)
    })
  }

  // Manages actions which rely on error information
  const ErrorHandler = function (error_data){
    // For each error, identify its location and store it in an analogously structured array
    // this is done for easy lookup later
    const colErrors = [];
    const rowErrors = [];
    const cellErrors = [[]]; // [col][row]
    error_data.forEach(error=>{
      const {column:col, row} = error;
      const hasCol = Number.isInteger(col);
      const hasRow = Number.isInteger(row);
      if(hasCol && hasRow){
        if(!cellErrors[col]) cellErrors[col] = [];
        if(!cellErrors[col][row]) cellErrors[col][row] = [];
        cellErrors[col][row].push(error)
      } else if (hasCol) {
        if(!colErrors[col]) colErrors[col] = [];
        colErrors[col].push(error)
      } else if (hasRow) {
        if(!rowErrors[row]) rowErrors[row] = []
        rowErrors[row].push(error)
      }
    })

    // get errors of all types for the cell located at col,row
    this.getErrs = (col,row)=>{
      const hasCol = Number.isInteger(col);
      const hasRow = Number.isInteger(row);
      const errs = {
        cellErrors:[],
        rowErrors:[],
        colErrors:[]
      }
      if(hasCol && hasRow && cellErrors[col] && cellErrors[col][row]){
        errs.cellErrors.push(...cellErrors[col][row])
      }
      if (hasCol && colErrors[col]) {
        errs.colErrors.push(...colErrors[col])
      }
      if (hasRow && rowErrors[row]) {
        errs.rowErrors.push(...rowErrors[row])
      }
      return errs
    };

    // Style HTML table row `rowElement` at position `tableRowIndex` based on `data`
    // to highlight errors
    this.highlightCells = (rowElement, data, tableRowIndex) => {
      const row = parseInt(data[0])-1;
      for (let i = 1; i < data.length; i++) {
        const col = i-1;
        const {cellErrors, rowErrors, colErrors} = this.getErrs(col,row);
        if(cellErrors.length>0){
          const errType = cellErrors.some(e=>e.severity==='error')?'error':'warning';
          $(`td:eq( ${i} )`,rowElement).addClass(`${errType}-cell`);
        }
        if(rowErrors.length>0){
          const errType = rowErrors.some(e=>e.severity==='error')?'error':'warning';
          $(`td:eq( ${i} )`,rowElement).addClass(`${errType}-row`);
        }
        if(colErrors.length>0){
          const errType = colErrors.some(e=>e.severity==='error')?'error':'warning';
          $(`td:eq( ${i} )`,rowElement).addClass(`${errType}-col`);
        }
      }
    };

    // Style XLSX document to highlight errors
    // this is pretty nasty code where we are directly manipulating the XLSX XML
    this.styleXLSX = (xlsx) => {
      // First, create the needed cell styles
      const style = xlsx.xl['styles.xml'];
      const fillGroup = $('fills', style);
      const styleGroup = $('cellXfs', style);

      // Create a XLSX style with a given BG color and return it's ID
      const addStyle = (bghex) => {
        const fillIndex = parseInt(fillGroup.attr('count'));
        fillGroup.append(`
          <fill>
            <patternFill patternType="solid">
              <fgColor rgb="FF${bghex.toUpperCase()}"/>
              <bgColor indexed="64"/>
            </patternFill>
          </fill>
        `);
        fillGroup.attr('count',`${fillIndex+1}`);
        
        const styleIndex = parseInt(styleGroup.attr('count'));
        styleGroup.append(`<xf numFmtId="0" fontId="0" fillId="${fillIndex}" borderId="0" applyFont="1" applyFill="1" applyBorder="1"/>`);
        styleGroup.attr('count',`${styleIndex+1}`);

        return `${styleIndex}`;
      }

      const styles = {
        "error-cell": addStyle('D2232A'),
        "warning-cell": addStyle('FFD200'),
        "error-axis": addStyle('F6D3D4'),
        "warning-axis": addStyle('FFEFAC'),
        "cross-axis": addStyle('FBE1C0')
      }

      // Next, for each cell, apply the appropriate style
      const sheet = xlsx.xl.worksheets['sheet1.xml'];
      const self = this;
      $('row c', sheet).each(function() {
        const cell = $(this);
        const [
          position, 
          colLetters, 
          rowNum
        ] = cell.attr('r').match(/^([A-Z]+)(\d+)/);
        const row = parseInt(rowNum)-1;
        const col = lettersToIndex(colLetters);
        const {cellErrors, rowErrors, colErrors} = self.getErrs(col,row);
        let cellStyle = null;
        if(cellErrors.length>0){
          cellStyle = cellErrors.some(e=>e.severity==='error')?'error-cell':'warning-cell';
        } else {
          if(rowErrors.length>0 ){
            cellStyle = rowErrors.some(e=>e.severity==='error')?'error-axis':'warning-axis';
          }
          if(colErrors.length>0){
            const colStyle = colErrors.some(e=>e.severity==='error')?'error-axis':'warning-axis';
            if(cellStyle && cellStyle!=colStyle){
              cellStyle = 'cross-axis'
            } else {
              cellStyle = colStyle
            }
          }
        }
        if(cellStyle){
          $(this).attr( 's', styles[cellStyle] );
        }
      });
    }

    return this
  }

  // Transform data to datatable-ready format.
  // Injects index numbers and empty rows where
  // they would appear in the original data
  const createDatatableRows = (data, index) => {
    const rows = [];
    const samples = data.map((sample,i)=>{
      // Prepend row index to sample data
      return [parseInt(index[i])+1, ...sample]
    });
    samples.forEach((sample,i)=>{
      // Add blank rows, accounting for "missing" header row by
      // increasing the row count by 1
      while (rows.length+1<index[i]){
        rows.push(sample.map(_=>""));
      }
      // Add sample row at correct index
      rows.push(sample);
    })
    return rows;
  }

  // Formats columns for datatables and adds an index column
  const createDatatableColumns = (columns) => {
    const data_cols = sample_data.columns.map((c,i)=>({data:i+1, title:c}));
    const index_col = {data:0, title:"•"} 
    return [index_col, ...data_cols];
  };

  // Adds excel-like column letter header to the table
  const addExcelHeader = (table, columns) =>{
    const excelHeader = $('<tr/>');
    columns.forEach((_,i)=>{
      const txt = i===0?"":indexToLetters(i-1)
      excelHeader.append(
        $("<th/>").text(txt)
      )
    })
    $(table.table().node()).find('thead').prepend(excelHeader)
  }

  // Initializes Selection events and sets up cross-table
  // filtering based on those events
  const selectionSetup = (sampleTable, detailTable)=>{
    const showErrorsFor = new Set();
    const showErrors = ()=>{
      const searchGroup = Array.from(showErrorsFor).join("|");
      if(searchGroup!==""){
        const searchRegex = `^(${searchGroup})$`;
        detailTable.columns(0).search(searchRegex, true, false).draw();
      } else {
        detailTable.columns(0).search('').draw();
      }
    }
    sampleTable.on('select', function(e, dt, type, indexes) {
      if (type === 'cell'){
        const numCells = indexes.filter(i=>i.column===0);
        //Deselect row numbers
        $.each(sampleTable.cells(numCells).nodes().to$(), function() {
          sampleTable.cell($(this)).deselect();
        })
        forEachLocation(indexes, sampleTable, loc=>showErrorsFor.add(loc));
        showErrors();
      }
    });
    sampleTable.on('deselect', function(e, dt, type, indexes) {
      if (type === 'cell'){
        forEachLocation(indexes, sampleTable, loc=>showErrorsFor.delete(loc));
        showErrors();
      }
    });
  }

  return {ErrorHandler, createDatatableRows, createDatatableColumns, addExcelHeader, selectionSetup, indexToLetters}
})();
