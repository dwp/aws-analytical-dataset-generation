import sys
from awsglue.transforms import *
from awsglue.dynamicframe import DynamicFrame
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as pf
from pyspark.sql.types import *

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'cut_off_time', 'margin_of_error'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

datasource0 = glueContext.create_dynamic_frame.from_catalog(database = "${database_name}", table_name = "${table_name_import_csv}", transformation_ctx = "datasource0")
datasource1 = glueContext.create_dynamic_frame.from_catalog(database = "${database_name}", table_name = "${table_name_export_csv}", transformation_ctx = "datasource1")

applymapping1 = ApplyMapping.apply(frame = datasource0, mappings = [("id", "string", "id", "string"), ("timestamp", "long", "import_timestamp", "long"), ("database", "string", "database", "string"), ("collection", "string", "collection", "string"), ("type", "string", "import_type", "string"), ("source", "string", "import_source", "string")], transformation_ctx = "applymapping1")
applymapping2 = ApplyMapping.apply(frame = datasource1, mappings = [("id", "string", "id", "string"), ("timestamp", "long", "export_timestamp", "long"), ("database", "string", "database", "string"), ("collection", "string", "collection", "string"), ("type", "string", "export_type", "string"), ("source", "string", "export_source", "string")], transformation_ctx = "applymapping2")

applymapping1_df = applymapping1.toDF()
applymapping2_df = applymapping2.toDF()

datasource_combined_df = applymapping1_df.join(applymapping2_df, ["id", "collection", "database"], how='fullouter')
datasource_combined_df_with_args1 = datasource_combined_df.withColumn('cut_off_time', pf.lit(args['cut_off_time']))
datasource_combined_df_with_args2 = datasource_combined_df_with_args1.withColumn('margin_of_error', pf.lit(args['margin_of_error']))
datasource_combined_with_new_column1 = datasource_combined_df_with_args2.withColumn("earliest_timestamp", pf.when((datasource_combined_df.export_timestamp.isNull()) | (datasource_combined_df.import_timestamp < datasource_combined_df.export_timestamp), datasource_combined_df.import_timestamp).otherwise(datasource_combined_df.export_timestamp))
datasource_combined_with_new_column2 = datasource_combined_with_new_column1.withColumn("latest_timestamp", pf.when((datasource_combined_with_new_column1.export_timestamp.isNull()) | (datasource_combined_with_new_column1.import_timestamp > datasource_combined_with_new_column1.export_timestamp), datasource_combined_with_new_column1.import_timestamp).otherwise(datasource_combined_with_new_column1.export_timestamp))
datasource_combined_with_new_column3 = datasource_combined_with_new_column2.withColumn("earliest_manifest", pf.when(datasource_combined_with_new_column2.export_timestamp == datasource_combined_with_new_column2.import_timestamp, "both").otherwise(pf.when((datasource_combined_with_new_column2.export_timestamp.isNull()) | (datasource_combined_with_new_column2.import_timestamp < datasource_combined_with_new_column2.export_timestamp), datasource_combined_with_new_column2.import_type).otherwise(datasource_combined_with_new_column2.export_type)))
datasource_combined_with_new_column4 = datasource_combined_with_new_column3.withColumn("before_cut_off", pf.when(datasource_combined_with_new_column3.earliest_timestamp <= datasource_combined_with_new_column3.margin_of_error.cast(LongType()), True).otherwise(False))
datasource_combined_with_new_column5 = datasource_combined_with_new_column4.withColumn("inside_margin", pf.when((datasource_combined_with_new_column4.before_cut_off == True) & (datasource_combined_with_new_column4.earliest_timestamp > datasource_combined_with_new_column4.cut_off_time.cast(LongType())), True).otherwise(False))
datasource_combined = DynamicFrame.fromDF(datasource_combined_with_new_column5, glueContext, "datasource_combined")

selectfields2 = SelectFields.apply(frame = datasource_combined, paths = ["id", "database", "collection", "import_timestamp", "import_type", "import_source", "export_timestamp", "export_type", "export_source", "earliest_timestamp", "latest_timestamp", "earliest_manifest", "before_cut_off", "inside_margin"], transformation_ctx = "selectfields2")

resolvechoice3 = ResolveChoice.apply(frame = selectfields2, database = "${database_name}", choice = "MATCH_CATALOG", table_name = "${table_name_parquet}", transformation_ctx = "resolvechoice3")

resolvechoice4 = ResolveChoice.apply(frame = resolvechoice3, choice = "make_struct", transformation_ctx = "resolvechoice4")

datasink5 = glueContext.write_dynamic_frame.from_catalog(frame = resolvechoice4, database = "${database_name}", table_name = "${table_name_parquet}", transformation_ctx = "datasink5")
job.commit()
