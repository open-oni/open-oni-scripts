#!/usr/bin/env python

import argparse
import fileinput
import os
import re
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
search_dir = '/var/local/data/newspapers/batches'



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
parser.add_argument("lccn", help="LCCN to be fixed")
parser.add_argument("bad_date", help="incorrect date")
parser.add_argument("new_date", help="corrected date")

args = parser.parse_args()


# Assign args
lccn = args.lccn
bad_date = args.bad_date
new_date = args.new_date

# Modify dates to file descriptor naming format
bad_date_fd = bad_date.replace('-', '')
bad_date_re = re.compile(bad_date_fd)
new_date_fd = new_date.replace('-', '')

# Handle optional redefined batch directory
if args.search_dir:
    if os.path.exists(args.search_dir): search_dir = args.search_dir
    else: print "{} does not exist".format(args.search_dir)



# Functions
# ---------
def find_bad_date_paths(lccn_path):
    bad_date_paths = []

    for root, dirs, files in os.walk(lccn_path):
        for d in dirs:
            if args.verbose:
                print "  Test if dir {} ~ bad date {}".format(d, bad_date_fd)
            if d.find(bad_date_fd) >= 0:
                if args.verbose:
                    print "    Dir {} ~ {}".format(d, bad_date_fd)
                bad_date_paths.append(os.path.join(root, d))

    if len(bad_date_paths) == 0:
        print "  Could not find batches with bad date {}".format(bad_date)
        sys.exit(1)

    return bad_date_paths


def find_lccn_paths():
    lccn_paths = []

    for root, dirs, files in os.walk(search_dir):
        for d in dirs:
            if args.verbose:
                print "  Test if dir {} ~ LCCN {}".format(d, lccn)
            if d.find(lccn) >= 0:
                if args.verbose:
                    print "    Dir {} ~ LCCN".format(d)
                lccn_paths.append(os.path.join(root, d))

    if len(lccn_paths) == 0:
        print "  Could not find batches identified by LCCN {}".format(lccn)
        sys.exit(1)

    return lccn_paths


def fix_dates(bad_date_path):
    for f in os.listdir(bad_date_path):
        if f.find('.xml') >= 0:
            file_path = os.path.join(bad_date_path, f)

            if not args.quiet:
                print "    Fix date in file {}".format(f)

            alto_file = 0
            alto_file_re = re.compile("[0-9]{4}\.xml")
            if alto_file_re.match(f): alto_file = 1

            # Don't replace dates if a dry run
            if not args.dry_run:
                # Update Alto XML
                # ---------------
                if alto_file:
                    # Set namespaces before parsing
                    ET.register_namespace("", "http://schema.ccs-gmbh.com/ALTO")

                    tree = ET.parse(file_path, parser=CommentRetainer())
                    root = tree.getroot()

                    # Replace bad date in string elements
                    for string in root.findall("PrintSpace//String"):
                        text = string.get("CONTENT")
                        if text.find(bad_date) >= 0:
                            string.set("CONTENT",
                                       text.replace(bad_date, new_date))

                    tree.write(file_path, encoding="UTF-8",
                               xml_declaration=True)
                # Update METS XML
                # ---------------
                else:
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

                    # Replace bad date in root's label attribute
                    label = root.get("LABEL")
                    if label.find(bad_date) >= 0:
                        root.set("LABEL", label.replace(bad_date, new_date))

                    # Replace bad date in dateIssued element
                    date = root.find(".//{http://www.loc.gov/mods/v3}dateIssued")
                    date.text = date.text.replace(bad_date, new_date)

                    tree.write(file_path, encoding="UTF-8",
                               xml_declaration=True)

                    # Restore structmap namespace that ET doesn't write
                    file = fileinput.FileInput(file_path, inplace=1)
                    for line in file:
                        print line.replace('<structMap>', '<structMap xmlns:np="urn:library-of-congress:ndnp:mets:newspaper">'),

                    fileinput.close()

            # Replace bad date in file name with new date
            # -------------------------------------------
            if (not alto_file and f.find(bad_date_fd) >= 0):
                new_file_fd = bad_date_re.sub(new_date_fd, f)
                new_file_path = os.path.join(bad_date_path, new_file_fd)

                if not args.quiet:
                    print "      Replace {} in file name with {}".format(bad_date_fd, new_date_fd)

                if not args.dry_run:
                    os.rename(file_path, new_file_path)

    # Replace bad date in path with new date
    # --------------------------------------
    new_date_path = bad_date_re.sub(new_date_fd, bad_date_path)

    if not args.quiet:
        print "\n    Replace {} in dir name with {}\n".format(bad_date_fd, new_date_fd)

    if not args.dry_run:
        os.rename(bad_date_path, new_date_path)

    # Update issue record in batch(_1).xml files
    # ------------------------------------------
    if not args.quiet:
        print "    Update dates in batch XML covering {}".format(lccn)

    if not args.dry_run:
        # Determine batch file and bad date paths
        batch_path_re = re.compile('^(.+)\/sn[0-9]{8}\/')
        batch_path = batch_path_re.match(bad_date_path).group(1)
        batch_files = [os.path.join(batch_path, "batch.xml"), os.path.join(batch_path, "batch_1.xml")]

        bad_date_path_tail_re = re.compile(".+\/({}\/.+)$".format(lccn))
        bad_date_path_tail = bad_date_path_tail_re.match(bad_date_path).group(1)

        for batch_file in batch_files:
            # Set namespaces before parsing
            ET.register_namespace("", "http://www.loc.gov/ndnp")
            #ET.register_namespace("ndnp", "http://www.loc.gov/ndnp")
            ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

            tree = ET.parse(batch_file, parser=CommentRetainer())
            root = tree.getroot()

            # Iterate through issue elements to update path of issue just fixed
            for issue in root.iter():
                if issue.text.find(bad_date_path_tail) >= 0:
                    issue_date = issue.get("issueDate")
                    print "      - Update issue {} replacing {} with {}\n".format(issue_date, bad_date, new_date)

                    issue.set("issueDate",
                              issue_date.replace(bad_date, new_date))

                    issue.text = issue.text.replace(bad_date_fd, new_date_fd)

            tree.write(batch_file, encoding="UTF-8", xml_declaration=True)

# Main
# ----
if  __name__ =='__main__':
    print "Searching {}".format(search_dir)
    lccn_paths = find_lccn_paths()

    for d in lccn_paths:
        if not args.quiet:
            print "\nSearch for bad dates in {}".format(d)
        bad_date_paths = find_bad_date_paths(d)

        for bdp in bad_date_paths:
            if not args.quiet:
                print "  Search for bad dates in {}".format(bdp)
            fix_dates(bdp)

