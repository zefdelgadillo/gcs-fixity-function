with fixity_dates as (
select distinct fixity_date
from `PROJECT_ID.fixity_data.records` 
order by fixity_date asc
),
ranked_fixity_dates as (
select row_number() over () as version, fixity_date
from fixity_dates
),
fixity_files as (
select distinct file_name
from `PROJECT_ID.fixity_data.records` 
),
ranked_fixity_files as (
select f.*, d.version
from `PROJECT_ID.fixity_data.records` f
join ranked_fixity_dates d on f.fixity_date = d.fixity_date
),
running_manifest as (
select distinct d.version, f.file_name, d.fixity_date, f2.file_md5sum as old_md5sum, f1.file_md5sum as new_md5sum, 
case
when (f2.file_md5sum = f1.file_md5sum) then ''
when (f2.file_md5sum is null and f1.file_md5sum is not null) then 'FILE_CREATED'
when (f2.file_md5sum is not null and f1.file_md5sum is null) then 'FILE_DELETED'
when (f1.file_md5sum is not null and f2.file_md5sum is not null and f1.file_md5sum != f2.file_md5sum) then 'NEW_VERSION_UPLOADED'
end as operation
from fixity_files f
join ranked_fixity_dates d on 1=1
left join ranked_fixity_files f1 on f.file_name = f1.file_name and d.version = (f1.version)
left join ranked_fixity_files f2 on f.file_name = f2.file_name and d.version = (f2.version + 1)
order by file_name, version desc
)
select file_name, fixity_date, old_md5sum, new_md5sum, operation from running_manifest where operation is not null;