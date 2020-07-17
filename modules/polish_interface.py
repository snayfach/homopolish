import os
import sys
import time
from Bio import SeqIO
from modules import mash
from modules import download
from modules import alignment
from modules import align2df
from modules import predict
from modules import polish
from modules.TextColor import TextColor
from modules.FileManager import FileManager


def print_system_log(stage):
    timestr = time.strftime("[%Y/%m/%d %H:%M]")
    sys.stderr.write(TextColor.GREEN + str(timestr) +" INFO: Stage: "+ stage + "\n" + TextColor.END)

def print_stage_time(stage, time):
    sys.stderr.write(TextColor.GREEN + "INFO: "+ stage + " TIME: " + str(time) + "\n" + TextColor.END)
        
def get_elapsed_time_string(start_time, end_time):
    """
    Get a string representing the elapsed time given a start and end time.
    :param start_time: Start time (time.time())
    :param end_time: End time (time.time())
    :return:
    """
    elapsed = end_time - start_time
    hours = int(elapsed / 60**2)
    mins = int(elapsed % 60**2 / 60)
    secs = int(elapsed % 60**2 % 60)
    time_string = "{} HOURS {} MINS {} SECS.".format(hours, mins, secs)

    return time_string

def polish_genome(assembly, model_path, sketch_path, threads, output_dir, minimap_args, mash_threshold, download_contig_nums):    
    
    out = []
    output_dir = FileManager.handle_output_directory(output_dir)

    for contig in SeqIO.parse(assembly, 'fasta'):
        timestr = time.strftime("[%Y/%m/%d %H:%M]")
        sys.stderr.write(TextColor.GREEN + str(timestr) +" INFO: RUN-ID: "+ contig.id + "\n" + TextColor.END)
        contig_output_dir = output_dir + '/' + contig.id
        contig_output_dir = FileManager.handle_output_directory(contig_output_dir)
        contig_name = contig_output_dir + '/' + contig.id +'.fasta'
        SeqIO.write(contig, contig_name, "fasta")
        
        screen_start_time = time.time()
        print_system_log('MASH SCREEN')
        mash_file = mash.screen(assembly, sketch_path, threads, contig_output_dir, mash_threshold, download_contig_nums, contig.id)
        screen_end_time = time.time()

        ncbi_id = mash.get_ncbi_id(mash_file)  
        
        #Would'nt polish if closely-related genomes less than 5
        if len(ncbi_id) > 5: 

            download_start_time = time.time()
            print_system_log('DOWNLOAD CONTIGS')
            url_list = download.parser_url(ncbi_id)
            db = download.download(contig_output_dir, ncbi_id, url_list)
            download_end_time = time.time()           


            pileup_start_time = time.time()
            print_system_log('PILE UP')
            db_npz = alignment.align(contig_name, minimap_args, threads, db, contig_output_dir)
            pileup_end_time = time.time()            
  

            align2df_start_time = time.time()           
            print_system_log('TO DATAFRAME')
            df = align2df.todf(contig_name, db_npz, contig_output_dir)
            align2df_end_time = time.time()
            
        
            predict_start_time = time.time()
            print_system_log('PREDICT')
            df = contig_output_dir + '/' + contig.id + '.feather'
            result = predict.predict(df, model_path, threads, contig_output_dir)
            predict_end_time = time.time()


            polish_start_time = time.time()
            print_system_log('POLISH')
            finish = polish.stitch(contig_name, result, contig_output_dir)
            polish_end_time = time.time()
            

            #calculating time
            screen_time = get_elapsed_time_string(screen_start_time, screen_end_time)
            download_time = get_elapsed_time_string(download_start_time, download_end_time)
            pileup_time = get_elapsed_time_string(pileup_start_time, pileup_end_time)
            align2df_time = get_elapsed_time_string(align2df_start_time, align2df_end_time)
            predict_time = get_elapsed_time_string(predict_start_time, predict_end_time)
            polish_time = get_elapsed_time_string(polish_start_time, polish_end_time)
            
            #print stage time
            print_stage_time('SCREEN', screen_time)
            print_stage_time('DOWNLOAD', download_time)
            print_stage_time('PILEUP', pileup_time)
            print_stage_time('TO DATAFRAME', align2df_time)
            print_stage_time('PREDICT', predict_time)
            print_stage_time('POLISH', polish_time)
            out.append(finish)
        else:
            out.append(contig_name)
    os.system('cat {} > {}/final.fasta'.format(' '.join(out), output_dir))