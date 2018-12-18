#!/usr/bin/env python

import argparse
from datetime import datetime
import fileinput
import glob
import os
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET

# XML parser to retain comments
class CommentRetainer(ET.XMLTreeBuilder):

   def __init__(self):
       ET.XMLTreeBuilder.__init__(self)
       # assumes ElementTree 1.2.X
       self._parser.CommentHandler = self.handle_comment

   def handle_comment(self, data):
       self._target.start(ET.Comment, {})
       self._target.data(data)
       self._target.end(ET.Comment)



# Defaults
# --------
search_dir = '/opt/openoni/data/batches'



# Arguments
# ---------
parser = argparse.ArgumentParser()

# Optional args
parser.add_argument("-d", "--dry_run", action="store_true",
                    help="don't make any changes to preview outcome")
parser.add_argument("-q", "--quiet", action="store_true",
                    help="suppress output")
parser.add_argument("-s", "--search_dir",
                    help="directory to search (default: /batches)")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="extra processing information")

# Positional args
parser.add_argument("bad_lccn", help="LCCN to be fixed")
parser.add_argument("correct_lccn", help="Correct LCCN")
parser.add_argument("start_date", help="Starting date (YYYY-MM-DD), inclusive")
parser.add_argument("end_date", help="Ending date (YYYY-MM-DD), inclusive")

args = parser.parse_args()


# Assign args
bad_lccn = args.bad_lccn
correct_lccn = args.correct_lccn
start_date = args.start_date
end_date = args.end_date

bad_lccn_re = re.compile(bad_lccn)

# Modify dates to file descriptor naming format
start_date_fd = start_date.replace('-', '')
start_date_re = re.compile(start_date_fd)
end_date_fd = end_date.replace('-', '')
end_date_re = re.compile(end_date_fd)

# Handle optional redefined batch directory
if args.search_dir:
    if os.path.exists(args.search_dir): search_dir = args.search_dir
    else: print "{0} does not exist".format(args.search_dir)



# Functions
# ---------
def find_effected_issue_paths(lccn_path):
    effected_issue_paths = []

    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

    for root, dirs, files in os.walk(lccn_path):
        for d in dirs:
            if len(d) == 10:
                d_dt = datetime.strptime(d[:8], "%Y%m%d")

                if d_dt >= start_date_dt and d_dt <= end_date_dt:
                    if args.verbose:
                        print "  Dir {0} between {1} and {2}".format(d, start_date_fd, end_date_fd)
                    effected_issue_paths.append(os.path.join(root, d))

    if len(effected_issue_paths) == 0:
        print "\n  Could not find batches within effected dates inside LCCN dir\n   {0}".format(lccn_path[len(search_dir):])

    return effected_issue_paths


def find_lccn_paths():
    lccn_paths = []

    for root, dirs, files in os.walk(search_dir):
        for d in dirs:
            if d.find(bad_lccn) >= 0:
                if args.verbose:
                    print "  Found {0}".format((root + '/' + d)[len(search_dir):])
                lccn_paths.append(os.path.join(root, d))

    if len(lccn_paths) == 0:
        print "\n  Could not find batches identified by LCCN\n  {0}".format(bad_lccn)

    return lccn_paths


def fix_lccns(effected_issue_path):
    for f in os.listdir(effected_issue_path):
        if f.find('.xml') >= 0:
            file_path = os.path.join(effected_issue_path, f)

            alto_file = 0
            alto_file_re = re.compile("[0-9]{4}\.xml")
            if alto_file_re.match(f): alto_file = 1

            # Don't replace lccn if a dry run
            if not args.dry_run:
                # Alto XML needs no changes

                # Update METS XML
                # ---------------
                if not alto_file:
                    if not args.quiet and not f[-6:] == "_1.xml":
                        print "    Fix lccn in file {0}".format(f)

                    # Set namespaces before parsing
                    ET.register_namespace("", "http://www.loc.gov/METS/")
                    ET.register_namespace("mix", "http://www.loc.gov/mix/")
                    ET.register_namespace("ndnp", "http://www.loc.gov/ndnp")
                    ET.register_namespace("premis", "http://www.oclc.org/premis")
                    ET.register_namespace("mods", "http://www.loc.gov/mods/v3")
                    ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")
                    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
                    ET.register_namespace("np", "urn:library-of-congress:ndnp:mets:newspaper")

                    tree = ET.parse(file_path, parser=CommentRetainer())
                    root = tree.getroot()

                    # Set correct lccn in first mods:identifier element
                    lccn_xml = root.find(".//{http://www.loc.gov/mods/v3}identifier")
                    if not args.quiet and not f[-6:] == "_1.xml":
                        print "      LCCN XML Identifier: {0}".format(lccn_xml.text)
                    lccn_xml.text = correct_lccn

                    tree.write(file_path, encoding="UTF-8",
                               xml_declaration=True)

                    # Restore structmap namespace that ET doesn't write
                    file = fileinput.FileInput(file_path, inplace=1)
                    for line in file:
                        print line.replace('<structMap>', '<structMap xmlns:np="urn:library-of-congress:ndnp:mets:newspaper">'),

                    fileinput.close()

    # Move effected issue to path with correct lccn
    # ---------------------------------------------
    new_issue_path = bad_lccn_re.sub(correct_lccn, effected_issue_path)

    if not args.quiet:
        print "    Move {0} to {1}".format(bad_lccn, correct_lccn)

    if not args.dry_run:
        os.renames(effected_issue_path, new_issue_path)

    # Copy/delete reel files
    # ----------------------
    reel_path_re = re.compile('^(.+\/(?:sn)?[0-9]+\/[0-9]{11})\/')
    effected_reel_path = reel_path_re.match(effected_issue_path).group(1)
    new_reel_path = reel_path_re.match(new_issue_path).group(1)

    reel_path_tail_re = re.compile('^(.+\/(?:sn)?[0-9]+\/[0-9]{11})$')
    effected_reel_path_tail = reel_path_tail_re.match(effected_reel_path).group(1)
    new_reel_path_tail = reel_path_tail_re.match(new_reel_path).group(1)
    reels_copied = []
    reels_deleted = []

    # Copy reel files to new lccn paths
    if not os.path.exists(new_reel_path +'/'+ new_reel_path[-11:] +'.xml'):
        if not args.quiet:
            print "      Copy reel files from {0} to {1}".format(effected_reel_path_tail, new_reel_path_tail)

        if not args.dry_run:
            for file in glob.glob(effected_reel_path +'/*.*'):
                shutil.copy2(file, new_reel_path)
        reels_copied.append(new_reel_path_tail)

    # Delete reel files if all issues moved to different lccn
    for reel_path, reel_issues, _ in os.walk(effected_reel_path):
        if len(reel_issues) == 0:
            if not args.quiet:
                print "      Delete reel files no longer needed from {0}".format(reel_path_tail_re.match(reel_path).group(1))

            if not args.dry_run:
                shutil.rmtree(effected_reel_path)
            reels_deleted.append(effected_reel_path_tail)

            # Also remove lccn directory if empty now
            lccn_path = effected_reel_path[:-12]
            for lccn_path, lccn_reels, _ in os.walk(lccn_path):
                if len(lccn_reels) == 0:
                    print "        Delete emptied containing lccn directory"

                    if not args.dry_run:
                        shutil.rmtree(lccn_path)

                # Only check from top directory if empty
                break

        # Only check from top directory if issue subdirectories
        break

    # Update lccns and reels in batch(_1).xml files
    # ---------------------------------------------
    if not args.quiet:
        print "    Update lccn in batch XML files to {0}".format(correct_lccn)

    # Determine batch file and bad date paths
    batch_path_re = re.compile('^(.+)\/(?:sn)?[0-9]+\/')
    batch_path = batch_path_re.match(effected_issue_path).group(1)
    batch_files = [os.path.join(batch_path, "batch.xml"), os.path.join(batch_path, "batch_1.xml")]

    effected_issue_path_tail_re = re.compile(".+\/({0}\/.+)$".format(bad_lccn))
    effected_issue_path_tail = effected_issue_path_tail_re.match(effected_issue_path).group(1)

    for batch_file in batch_files:
        # Set namespaces before parsing
        ET.register_namespace("", "http://www.loc.gov/ndnp")
        ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

        tree = ET.parse(batch_file, parser=CommentRetainer())
        root = tree.getroot()

        # Iterate through issue elements to update lccns & paths
        issues = root.findall(".//{http://www.loc.gov/ndnp}issue")
        for issue in issues:
            if issue.text.find(effected_issue_path_tail) >= 0:
                issue_date = issue.get("issueDate")
                issue_lccn = issue.get("lccn")
                if not args.quiet and not batch_file[-6:] == "_1.xml":
                    print "      Update issue {0} replacing {1} with {2}".format(issue_date, bad_lccn, correct_lccn)

                issue.set("lccn", correct_lccn)

                issue.text = issue.text.replace(bad_lccn, correct_lccn)

        # Update reel elements
        if len(reels_copied) or len(reels_deleted):
            reels = root.findall(".//{http://www.loc.gov/ndnp}reel")

            for reel_copied in reels_copied:
                copied_reel_added = 0
                copied_reel_number = int(reel_copied[-11:])
                copied_reel_index = 0
                reel_index = 0

                for reel in reels:
                    # Check if copied reel has already been added
                    if (not copied_reel_added) and reel.text.find(reel_copied) >= 0:
                        if args.verbose and not batch_file[-6:] == "_1.xml":
                            print "      Copied reel {0} already added to batch XML".format(reel_copied)

                        copied_reel_added = 1
                        break

                    # Track where copied reel should be inserted
                    if not copied_reel_index:
                        reel_number = int(reel.text.split('/')[1])

                        if copied_reel_number < reel_number:
                            copied_reel_index = len(issues) + reel_index
                            break

                        elif copied_reel_number == reel_number:
                            # Compare lccn of copied reel
                            if int(correct_lccn[2:]) < int(reel.text.split('/')[0][2:]):
                                copied_reel_index = len(issues) + reel_index
                                break

                    reel_index += 1


                # Add copied reel to batch reels
                if not copied_reel_added:
                    if not args.quiet and not batch_file[-6:] == "_1.xml":
                        print "      Adding copied reel {0} to batch XML".format(reel_copied)

                    reel_number = reel_copied.split('/')[1]
                    reel_element = ET.Element("reel", {"reelNumber": reel_number})
                    reel_element.text = reel_copied +'/'+ reel_number +'.xml' 
                    reel_element.tail = '\n\t'

                    if copied_reel_index:
                        root.insert(copied_reel_index, reel_element)
                    else:
                        root.append(reel_element)


            for reel_deleted in reels_deleted:
                deleted_reel_removed = 0
                for reel in reels:
                    # Check if deleted reels have been removed
                    if (not deleted_reel_removed) and reel.text.find(reel_deleted) >= 0:
                        if not args.quiet and not batch_file[-6:] == "_1.xml":
                            print "      Removing deleted reel {0} found in batch XML".format(reel_deleted)

                        # Remove deleted reel from batch reels
                        root.remove(reel)
                        deleted_reel_removed = 1

        if not args.dry_run:
            tree.write(batch_file, encoding="UTF-8", xml_declaration=True)

# Main
# ----
if  __name__ =='__main__':
    print "Searching for bad LCCN {0} in\n{1}".format(bad_lccn, search_dir)
    lccn_paths = find_lccn_paths()

    for d in lccn_paths:
        if not args.quiet:
            print "\nSearch for effected issues in:\n{0}".format(d[len(search_dir):])
        effected_issue_paths = find_effected_issue_paths(d)

        for eip in effected_issue_paths:
            if not args.quiet:
                print "\n  Fix effected issue at {0}".format(eip[(len(search_dir) + len(d[len(search_dir):])):])
            fix_lccns(eip)

    1

