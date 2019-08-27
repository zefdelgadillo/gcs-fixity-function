with fixity_dates as (
select distinct fixity_date
from `PROJECT_ID.fixityData.records` 
order by fixity_date asc
),
ranked_fixity_dates as (
select row_number() over () as version, fixity_date
from fixity_dates
),
fixity_files as (
select distinct file_name
from `PROJECT_ID.fixityData.records` 
),
ranked_fixity_files as (
select f.*, d.version
from `PROJECT_ID.fixityData.records` f
join ranked_fixity_dates d on f.fixity_date = d.fixity_date
),
running_manifest as (
select distinct d.version, f.file_name, f1.file_size, f1.file_updated_date, d.fixity_date, f1.file_md5sum as file_md5sum
from fixity_files f
join ranked_fixity_dates d on 1=1
left join ranked_fixity_files f1 on f.file_name = f1.file_name and d.version = (f1.version)
order by file_name, version desc
),
ranked_manifest as (
select file_name, file_size, file_updated_date, fixity_date, file_md5sum,
rank() over (partition by file_name order by version desc) as rank
from running_manifest)
select file_name, file_size, file_updated_date, fixity_date, file_md5sum from ranked_manifest where rank = 1 and file_md5sum is not null;
