/*select distinct(meta_responsiblename) from assignments where LEFT(preload_a1b,1)='1' */
/*select meta_responsiblename from assignments where LEFT(preload_a1b,1)='1' */
/*select meta_responsiblename from assignments where preload_a1b='11'*/
/*select (meta_responsiblename, preload_a1b) from assignments where LEFT(preload_a1b,1)='1'*/
/*SELECT login, role, workingarea FROM susouser WHERE role in ('head of district','zonal supervisor', 'area supervisor', 'supervisor', 'interviewer') AND LEFT(workingarea,1)='1'*/
/*select meta_responsiblename, preload_a1b,preload_a2b,preload_a3b from assignments where LEFT(preload_a1b,1)='1'*/

/*SELECT meta_responsiblename, meta_receivedbytabletatutc FROM assignments WHERE preload_a2b='1103';*/
/*select login, workingarea from susouser where login='coor01'*/
/*SELECT DISTINCT role FROM susouser;*/
/*alter table susouser add column is_active BOOLEAN DEFAULT TRUE;*/
/*select * from susouser where login='zonal01'*/
/*select workingarea from susouser where login='coor02'*/
delete from susouser where login='coor06'
