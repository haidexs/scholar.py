#! /usr/bin/env python
#
# This code checks whether an author has publications in a specified "venue"
# between two specified years based on Google Scholar search results.
#
# Written by Zhulin Yu, Jun. 2017
#
# Input:
#    File name of author name list
#    Phrase that defines the "venue"
#    Start year
#    End year
#
# Output:
#    A .txt file listing authors with publications and total # of publications.
#
# e.g.,:
# python publish_or_not.py -nl "names.txt" -p "Learning Analytics" --after 2013 --before 2017 -o "output.txt"

from simple_scholar import *
import os
import sys
import random
import time
import pandas
# reload(sys)
# sys.setdefaultencoding('utf8')
from argparse import ArgumentParser
from fake_useragent import UserAgent

import ipdb

import progressbar
bar = progressbar.ProgressBar(maxval=20, \
    widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])

def send_email(err_msg):
    # Import smtplib for the actual sending function
    import smtplib

    # Import the email modules we'll need
    from email.mime.text import MIMEText

    # Message Content
    msg = MIMEText(err_msg)
    msg['Subject'] = "Google Scholar Requests Blocked"
    sender = "haidexs@gmail.com"
    msg['From'] = sender
    # recipients = ['zy2247@tc.columbia.edu ']
    recipients = ['zy2247@tc.columbia.edu']
    msg['To'] = ", ".join(recipients)

    # Send through Gmail
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login("haidexs", "EdAnna070315")

    server.sendmail(sender, recipients, msg.as_string())
    server.quit()

if __name__ == "__main__":
    # parse input options
    parser = ArgumentParser()
    parser.add_argument("-nl", "--namelist",
                      dest="namelist", type = str,
                      help="File name of the name list.")

    parser.add_argument("-o", "--output_file",
                      dest="output_file", default='Output.txt', type = str,
                      help="Name of output file")

    group1 = parser.add_argument_group('group1', 'essential options')

    group1.add_argument("-p", "--phrase",
                      dest="phrase", type = str, default = None,
                      help="Phrase that defines the venue. Results must contrain exact phrase")

    group1.add_argument('-a', '--author', metavar='AUTHORS', default=None,
                     help='Author name(s)')
    group1.add_argument('-A', '--all', metavar='WORDS', default=None, dest='allw',
                     help='Results must contain all of these words')
    group1.add_argument('-s', '--some', metavar='WORDS', default=None,
                     help='Results must contain at least one of these words. Pass arguments in form -s "foo bar baz" for simple words, and -s "a phrase, another phrase" for phrases')
    group1.add_argument('-n', '--none', metavar='WORDS', default=None,
                     help='Results must contain none of these words. See -s|--some re. formatting')
    group1.add_argument('-t', '--title-only', action='store_true', default=False,
                     help='Search title only')
    group1.add_argument('-P', '--pub', metavar='PUBLICATIONS', default=None,
                     help='Results must have appeared in this publication')
    group1.add_argument('--after', metavar='YEAR', default=None,
                     help='Results must have appeared in or after given year')
    group1.add_argument('--before', metavar='YEAR', default=None,
                     help='Results must have appeared in or before given year')
    group1.add_argument('--no-patents', action='store_true', default=False,
                     help='Do not include patents in results')
    group1.add_argument('--no-citations', action='store_true', default=False,
                     help='Do not include citations in results')
    group1.add_argument('-C', '--cluster-id', metavar='CLUSTER_ID', default=None,
                     help='Do not search, just use articles in given cluster ID')
    group1.add_argument('-c', '--count', type = int, default=None,
                     help='Maximum number of results')

    group2 = parser.add_argument_group('group2', 'Output format') # control output format
    
    group2.add_argument('--txt', action='store_true',
                     help='Print article data in text format (default)')
    group2.add_argument('--txt-globals', action='store_true', default = True, 
                     help='Like --txt, but first print global results too')
    group2.add_argument('--csv', action='store_true',
                     help='Print article data in CSV form (separator is "|")')
    group2.add_argument('--csv-header', action='store_true',
                     help='Like --csv, but print header with column names')
    group2.add_argument('--citation', metavar='FORMAT', default=None,
                     help='Print article details in standard citation format. Argument Must be one of "bt" (BibTeX), "en" (EndNote), "rm" (RefMan), or "rw" (RefWorks).')
    

    group3 = parser.add_argument_group('group3', 'Miscellaneous')

    group3.add_argument('--cookie-file', metavar='FILE', default=None,
                     help='File to use for cookie storage. If given, will read any existing cookies if found at startup, and save resulting cookies in the end.')
    group3.add_argument('-d', '--debug', action='count', default=0,
                     help='Enable verbose logging to stderr. Repeated options increase detail of debug output.')
    group3.add_argument('-v', '--version', action='store_true', default=False,
                     help='Show version information')
    #parser.add_argument_group(group)

    group4 = parser.add_argument_group('group4', 'Proxy settings')

    group4.add_argument('-pl', '--proxylist',
                      dest='proxylist_file', type = str,
                      help="File name of the proxies list.")
    # group4.add_argument('-al', '--agentlist',
    #                     dest = 'agentlist_file', type = str,
    #                     help = 'File name of the agent list')
    group4.add_argument('-po', '--proxyon',
                        dest = 'proxy_switch', type = int,
                        help = '1 = proxy on; 0 = proxy off')

    options = parser.parse_args()

    # read names from namelist file
    file_namelist = options.namelist

    if not os.path.exists(file_namelist):
        raise ValueError("Name list file does not exist!")
    else:
        with open(file_namelist) as f:
            names = f.readlines()
            names = [x.strip() for x in names]

    output_file = options.output_file

    if options.after > options.before:
        raise ValueError("Start year is after end year!")

    if os.path.exists(output_file):
        overwrite = raw_input("Output file " + output_file + " exists. Want to overwrite (y/n)?: ")
        if overwrite == "y" or overwrite == "Y":
            ofid = open(output_file, 'w')
        elif overwrite == "n" or overwrite == "N":
            output_file = raw_input("Give a new output file name: ")
            ofid = open(output_file, 'w')
        else:
            raise ValueError("Unexpected input.")
    else:
        ofid = open(output_file, 'w')

    ofid.write("Google Scholar Search Result\n")
    ofid.write("Venue: " + options.phrase + "\n")
    ofid.write("Years: " + str(options.after) + " - " + str(options.before) + "\n")
    ofid.write("==========================\n")
    ofid.write("Name         Publish?         Total\n")
    ofid.close()

    # Using proxies to scrape
    if options.proxy_switch == 1:
        if not os.path.exists(options.proxylist_file):
            raise ValueError("Proxy list file does not exist!")
        else:
            with open(options.proxylist_file) as f:
                proxies_all = f.readlines()
                proxies_all = [x.strip() for x in proxies_all]

        ua = UserAgent()
        ua.update()
        print("Agent Database Prepared (based on UserAgent)!\n")

        rest_mean = 60*10 # seconds
        rest_std = 60*2 # seconds
        rest_n_request = 15
        req_intv_mean = 90
        req_intv_std = 35


    crnt_n = 0
    total_names = len(names)
    bar.start()
    
    # Start scraping for each name
    remain_names = names[:]
    for name in names:
        
        # for this name
        options.author = name

        # setting up request
        querier = ScholarQuerier()
        settings = ScholarSettings()
        querier.apply_settings(settings)

        if options.cluster_id:
            query = ClusterScholarQuery(cluster=options.cluster_id)
        else:
            query = SearchScholarQuery()
            if options.author:
                query.set_author(options.author)
            if options.allw:
                query.set_words(options.allw)
            if options.some:
                query.set_words_some(options.some)
            if options.none:
                query.set_words_none(options.none)
            if options.phrase:
                query.set_phrase(options.phrase)
            if options.title_only:
                query.set_scope(True)
            if options.pub:
                query.set_pub(options.pub)
            if options.after or options.before:
                query.set_timeframe(options.after, options.before)
            if options.no_patents:
                query.set_include_patents(False)
            if options.no_citations:
                query.set_include_citations(False)

        if options.count is not None:
            options.count = min(options.count, ScholarConf.MAX_PAGE_RESULTS)
            query.set_num_page_results(options.count)

        # show progress
        crnt_n = crnt_n + 1
        bar.update(round(float(crnt_n)/total_names*20))
        if crnt_n%rest_n_request == 0:
            rest_time = abs(random.normalvariate(rest_mean, rest_std))
            print(str(rest_n_request) + " requests finished! Rest for " + str(rest_time) + " seconds!\n")
            time.sleep(rest_time)
            
        # Choose one proxy and check if it is working.
        if options.proxy_switch == 1:
            proxy_host_port = random.choice(proxies_all)
            while not proxy_check(proxy_host_port):
                proxy_host_port = random.choice(proxies_all)

            agent_str = str(ua.random)

            # sleep for random seconds defined by req_intv_mean and req_intv_std
            req_intv = abs(random.normalvariate(req_intv_mean, req_intv_std))
            print("Sleep " + str(req_intv) + " sec.\n")
            if crnt_n > 1:
                time.sleep(req_intv)

        else:
            proxy_host_port = ''
            agent_str = ''

        # Send request
        returned_html = querier.send_query(query, proxy_host_port, agent_str)
        
        # Check if valid result returned
        if returned_html == None:
            flag = "Failure"
            total_publish = 0
            print("Request denied by Google! Proxy: " + proxy_host_port)
            # we are blocked by Google.

            # print the remaining names to a new name list file
            remain_namelist_file = ("remain_" + time.strftime("%m-%d-%y-%H%M") + "_" +
                options.namelist.split('/')[-1])
            with open(remain_namelist_file, 'w') as f:
                for ni in remain_names:
                    f.write(ni + "\n")
            print("Remaining names output to " + remain_namelist_file + "!\n")
            send_email("Blocked! Remaining names are in " + remain_namelist_file + ".")
            raise ValueError("Blocked by Google!")

        else:
            total_publish = txt(querier, with_globals=options.txt_globals)
            print("Result Returned: " + name + " through " + proxy_host_port)
            if total_publish == 0:
                flag = "No"
            elif total_publish > 0:
                flag = "Yes"
            else:
                raise ValueError("Returned Total Publication Num is Negative!")

            if options.cookie_file:
                querier.save_cookies()

        # write to output file
        ofid2 = open(output_file, 'aw')
        ofid2.write(name + "    " + flag + "    " + str(total_publish) + "\n")
        ofid2.close()

        remain_names.remove(name)

        remain_namelist_file = ("remain_" + options.namelist.split('/')[-1])
        with open(remain_namelist_file, 'w') as f:
            for ni in remain_names:
                f.write(ni + "\n")
        print("Remaining names output to " + remain_namelist_file + "!\n")

    # ofid.close()
    bar.finish()
