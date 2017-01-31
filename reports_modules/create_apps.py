#!python3
'''Module for creating the applications tab (with Excel formulas)'''
from reports_modules.excel_base import safe_write, make_excel_indices

def lookup_roster_field(x,roster,field):
    return roster.loc[x,field]

def reduce_and_augment_apps(cfg, dfs, debug):
    '''Restrict an applications table to those apps for students in roster
    then add lookup and calculated fields, finally sorting for output'''
    # first reduce
    df = dfs['applications']
    id_list = set(dfs['roster'].index)
    df = df[df['hs_student_id'].isin(id_list)].copy()

    # then add lookup columns
    roster_fields = ['GPA','ACT','Race/ Eth']
    for field in roster_fields:
        df[field] = df['hs_student_id'].apply(lookup_roster_field,
            args=(dfs['roster'],field))


    # then add calculated columns (for use internally, not publishing)
    print(df.columns)

    # finally sort
    dfs['apps'] = df

def push_column(columns, letters, label, formula, fmt=None):
    '''Adds an item to a list of length 3 lists that define columns with
    col0=Excel header, col1=label, col2=formula; replaces %label% with
    the corresponding letter in Excel for that letter plus a _r_'''
    col_ltr = {x[1]:x[0] for x in columns}
    new_col = [letters[len(columns)],label]
    tokens = formula.split('%')
    for i in range(1,len(tokens),2):
        tokens[i] = col_ltr[tokens[i]]+'_r_'
    new_col.append(''.join(tokens))
    new_col.append(fmt)
    columns.append(new_col)
    return columns

def make_apps_tab(writer, f_db, dfs, cfg, debug):
    '''Creates the Excel tab for applications only for students in roster'''
    if debug:
        print('Writing applications tab...',flush=True,end='')

    df = dfs['apps']
    wb = writer.book
    sn = 'Applications'
    ws = wb.add_worksheet(sn)

    # Now define a list of columns and how they are constructed

    # First the columns that are direct from the df
    cols = cfg['app_fields']
    col_letters = make_excel_indices() # column headers used in Excel
    current_use = ['use_df']*len(cols)
    fmts = [None]*len(cols)
    master_cols = [list(a) for a in zip(col_letters,cols,current_use,fmts)]

    format_catch = cfg['app_format_catch'] # for coloring df fields
    for x in master_cols:
        if x[1] in format_catch:
            x[3] = format_catch[x[1]]

    # Second define the calculated columns
    for app_column in cfg['applications_calculations']:
        for column_name in app_column: # there's only one, but need to deref
            formula = app_column[column_name]['formula']
            fmt = app_column[column_name]['format']
            push_column(master_cols, col_letters,
                    column_name, formula, fmt)

    # Now write the column headers:
    for i in range(len(master_cols)):
        col = master_cols[i]
        ws.write(0,i,col[1],f_db[(col[3] if col[3] else 'bold')])

    # Write data based on master_cols key
    start_row = 1
    end_row = len(df)
    end_col = len(master_cols)-1

    row = start_row
    for i, app_data in df.iterrows():
        sr = str(row+1)
        for c in range(len(master_cols)):
            letter, label, formula, fmt = master_cols[c]
            if formula == 'use_df':
                safe_write(ws, row, c, app_data[label],n_a='')
            else:
                safe_write(ws, row, c, formula.replace('_r_',sr))
        row += 1

    # Do names
    col_ltr = {x[1]:x[0] for x in master_cols}
    for name, label in cfg['application_names'].items():
    #for [name,label] in name_list:
        col = col_ltr[label]
        wb.define_name(name,'='+sn+'!$'+col+'$'+str(start_row+1)+':$'+
            col+'$'+str(end_row+1))

    ws.autofilter(start_row-1,0, end_row, end_col)
    ws.freeze_panes(start_row,6)
    if debug:
        print('(now {} apps)'.format(len(df)))
        print('Done!',flush=True)
