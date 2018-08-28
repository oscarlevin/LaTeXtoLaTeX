
import logging
import hashlib
import re

import component

#################

def sha1hexdigest(text):
    """Return the sha1 hash of text, in hexadecimal."""

    the_text = text
    sha1 = hashlib.sha1()

    try:
        sha1.update(the_text.encode('utf-8', errors="ignore"))
    except UnicodeDecodeError:
        sha1.update(the_text)

    this_sha1 = sha1.hexdigest()

    component.sha1of[this_sha1] = {'original_text' : the_text}

    return(this_sha1)

#################

def sha1hide(txt, tag):

    thetext = txt.group(1)

    the_hash = sha1hexdigest(thetext)

    if tag == "comment":
        return "ACOMMB" + the_hash + "ENDZ"
    else:
        return "A" + tag + "B" + the_hash + "ENDZ"
        
#################

def sha1undigest(txt):

    try:
        the_tag = txt.group(1)
        the_sha1key = txt.group(2)
    #    return "<" + the_tag + component.sha1of[the_sha1key]['original_text'] + "</" + the_tag + ">"
        return component.sha1of[the_sha1key]['original_text']

    except (AttributeError, IndexError) as e:
        the_sha1key = txt.group(1)
        return component.sha1of[the_sha1key]['original_text']

#################

def strip_brackets(text,lbrack="{",rbrack="}",depth=0):
    """Convert {{text}}} to text}.

    """

    thetext = text
    current_depth = 0

    if not thetext:
        return ""

    while thetext and thetext[0] == lbrack and thetext[-1] == rbrack:
        current_depth += 1
        firstpart,secondpart = first_bracketed_string(thetext,0,lbrack,rbrack)
        firstpart = firstpart[1:-1]
        if not firstpart:
            return secondpart
        elif depth and current_depth >= depth:
            return firstpart
        thetext = firstpart + secondpart

    return thetext

###################

def first_bracketed_string(text, depth=0, lbrack="{", rbrack="}"):
    """If text is of the form {A}B, return {A},B.

    Otherwise, return "",text.

    """

    thetext = text.lstrip()

    if not thetext:
        print "Error: no text"
        component.error_messages.append("empty string sent to first_bracketed_string()")
        return ""

    previouschar = ""
       # we need to keep track of the previous character becaause \{ does not
       # count as a bracket

    if depth == 0 and thetext[0] != lbrack:
        return "",thetext

    elif depth == 0:
        firstpart = lbrack
        depth = 1
        thetext = thetext[1:]
    else:
        firstpart = ""   # should be some number of brackets?

    while depth > 0 and thetext:
        currentchar = thetext[0]
        if currentchar == lbrack and previouschar != "\\":
            depth += 1
        elif currentchar == rbrack and previouschar != "\\":
            depth -= 1
        firstpart += currentchar
        if previouschar == "\\" and currentchar == "\\":
            previouschar = "\n"
        else:
            previouschar = currentchar

        thetext = thetext[1:]

    if depth == 0:
        return firstpart, thetext
    else:
        print "Error: no matching bracket",lbrack,"in",thetext,"XX"
  #      return "",thetext
        print "returning",firstpart[1:100], "\nPLUS MORE\n"
        return "",firstpart[1:]   # firstpart should be everything
                                  # but take away the bracket that doesn't match


#################

def replacemacro(text,macroname,numargs,replacementtext):
    """Expand a LaTeX macro in text.

    """

    if text == "":
        logging.debug("replacing macro %s in an empty string", macroname)
        return ""

    if "\\"+macroname not in text:
        return text

    # there is a tricky situation when a macro is being replaced by nothing.  if it is
    # alone on a line, then you just introduced a paragraph break.  it seems we must
    # treat that as a special case


    thetext = text
    global a_macro_changed

    a_macro_changed = 1

    while a_macro_changed:   # maybe change to:  while "\\"+macroname in text:

        # first, the special case described above, which we are not really handling right
        if not replacementtext:
            while a_macro_changed:
                logging.debug("replacing macro %s by nothing in: %s", macroname, re.sub("\s{2,}","\n",thetext.strip())[:30])
                a_macro_changed = 0
                thetext = re.sub(r"\n\\("+macroname+r")\s*({[^{}]*})\s",
                                 lambda match: replacemac(match,numargs,"\n"),thetext,1,re.DOTALL)
        a_macro_changed = 0

        thetext = re.sub(r"\\("+macroname+r")\**(([0-9]|\b)+.*)",lambda match: replacemac(match,numargs,replacementtext),thetext,1,re.DOTALL)

    return thetext

##############

def replacemac(txt,numargs,replacementtext):

    this_macro = txt.group(1)
    text_after = txt.group(2)

    if numargs:
        text_after = text_after.lstrip()

    if text_after.startswith("["):
        logging.debug("found square group")
        squaregroup, text_after = first_bracketed_string(text_after,0,"[","]")
        text_after = text_after.lstrip()
        # Currently we ignore the squaregroup.  What should we do with it?

     # first a hack to handle some oddly formed macro calls
    try:
        first_character = text_after[0]
    except IndexError:
        first_character = ""

    if numargs and first_character  not in ["{","\\"] and first_character not in r"0123456789":
        logging.debug("found %s but it has no argument %s", this_macro, text_after[:50])
        return text_after

    if first_character in "0123456789":   # wrap it in {} and proceed normally
        logging.debug("found that the argument is a number")
        text_after = re.sub("^([0-9])",r"{\1}",text_after,1)
        logging.debug("now the text after starts: %s", text_after[:20])

    if first_character == r"\\":   # wrap the argument in {} and proceed normally
        logging.debug("found that the argument is another macro")
        text_after = re.sub(r"^\\([a-zA-Z]+)",r"{\\\1}",text_after,1)

    global a_macro_changed
    a_macro_changed += 1

    arglis=[""]      # put a throw-away element 0 so that it is less confusing
                     # when we assign to the LaTeX "#N" argmuments

    for ar in range(numargs):
            try:
                theitem, text_after = first_bracketed_string(text_after)
            except ValueError:
                logging.error("no text_after in replacemac for argument %s of %s", ar, this_macro)
                logging.error("text_after begins %s", text_after[:40])
                if ar:
                    logging.error("arglis so far is %s", arglis)
                theitem = ""
                # below is to fail gracefully when there is an error.
                # need to come up with a better way
            if not theitem:  # probably missing close bracket
                logging.error("was scanning argument %s of %s before text_after %s", ar, this_macro, text_after[:20])
                logging.error("missing brace?  guess to stop at end of line")
                if "\n" in text_after:
                    theitem, text_after = text_after.split("\n",1)
                else:
                    theitem = ""
            theitem = strip_brackets(theitem)
            theitem = re.sub(r"\\",r"\\\\",theitem)  # This is tricky.  We are using the extracted LaTeX
                                                   # in a substitution, so we should think of it as code.
                                                   # Therefore we need to excape the backslashes.
            arglis.append(theitem)

# confused about which of the next two lines is correct
    macroexpanded = replacementtext
#    macroexpanded = re.sub(r"\\",r"\\\\",replacementtext)

    for arg in range(1,numargs+1):
        mysubstitution = "#"+str(arg)
        macroexpanded = re.sub(mysubstitution,arglis[arg],macroexpanded)

    return macroexpanded + text_after


#################

def text_before(text, target):
    """If text is of the form *target*, return (*,target*).
    Otherwise, return ("",text)
    Note that target can be a tuple.
    """

    thetext = text
    thetarget = target

    if isinstance(thetarget, str):
        thetarget = [thetarget]
    thetarget = tuple(thetarget)

    firstpart = ""

    while thetext and not thetext.startswith(thetarget):
        firstpart += thetext[0]
        thetext = thetext[1:]

    if thetext:
        return (firstpart,thetext)
    else:
        return("",text)

#################

def argument_of_macro(text,mac,argnum=1):
    """Return the argument (without brackets) of the argnum
       argument of the first appearance of the macro \mac
       in text.

    """

    searchstring = r".*?" + r"\\" + mac + r"\b" + r"(.*)"
    # the ? means non-greedy, so it matches the first appearance of \\mac\b

    try:
        text_after = re.match(searchstring,text,re.DOTALL).group(1)
    except AttributeError:
        print "Error: macro " + mac + " not in text"
        return ""

    for _ in range(argnum):
        the_argument, text_after = first_bracketed_string(text_after)

    the_argument = strip_brackets(the_argument)

    return the_argument

#################

def magic_character_convert(text, mode):
    """ replace & and < by 
        &amp; or \amp or <ampersand /> or TMPAMPAMP 
            and 
        &lt; or \lt or <less /> or TMPLESSLESS
            depending on whether mode is
        code or math or text or hide

    """

 ### need "hide" as a 3rd parameter, so we can get TMPmathAMPAMP for example
 ### that way we can hide math first, and then do text that includes math

    the_text = text

    the_text = re.sub(r"&", "TMPhideAMPAMP", the_text)
    the_text = re.sub(r"<", "TMPhideLESSLESS", the_text)

    if mode == "code":
     #   the_text = re.sub("TMPhideAMPAMP", r"&amp;", the_text)
     #   the_text = re.sub("TMPhideLESSLESS", r"&le;", the_text)
        the_text = re.sub("TMPhideAMPAMP", r"<ampersand />", the_text)
        the_text = re.sub("TMPhideLESSLESS", r"<less />", the_text)
    elif mode == "math":
        the_text = re.sub("TMPhideAMPAMP", r"\\amp", the_text)
        the_text = re.sub("TMPhideLESSLESSvar", r"<var", the_text)
        the_text = re.sub("TMPhideLESSLESS", r"\\le", the_text)
    elif mode == "text":
        the_text = re.sub("TMPhideAMPAMP", r"&amp;", the_text)
        the_text = re.sub("TMPhideLESSLESS", r"&lt;", the_text)
        
# also need an "unhide" mode

    return the_text

###############

def tag_to_numbered_tag(tag, text):

    # turn each instance of <tag>...</tag> into <tagN>...</tagN> where N
    # increments from 1 to the number of times that tag appears
    # tags are counted by component.lipcounter

    # be careful of tags that can also be self-closing

    the_text = text

    print "in tag_to_numbered_tag for",tag,"tag"
    find_start_tag = r"(<" + tag + ")"
    find_start_tag += "(>| [^/>]*>)"
    find_end_tag = r"(</" + tag + ")>"

    component.something_changed = True
#    while "<tag " in the_text or "<tag>" in the_text:
    while component.something_changed:
        component.something_changed = False
        the_text = re.sub(find_start_tag + "(.*?)" + find_end_tag,
                          lambda match: tag_to_numbered_t(tag, match),
                          the_text, 0, re.DOTALL)

    return the_text

#-------------#

def tag_to_numbered_t(tag, txt):

    the_tag = tag
    the_start1 = txt.group(1)
    the_start2 = txt.group(2)
    the_text = txt.group(3)
    the_end = txt.group(4)

    component.something_changed = True

#    if the_tag == "task":
#        print "the_tag", the_tag, "the_start1", the_start1, "the_start2", the_start2, "the_end", the_end
    if "<" + the_tag + " " in the_text or "<" + the_tag + ">" in the_text:
#        if the_tag == "task":
#          print "++++++++++++++nested tag", the_tag, " in", the_text + the_end + ">"
#          print "///////nested tag in"
#        before_tag = re.sub(r"(.*?)(<" + the_tag + "(>| [^/>]*).*$)", r"\1", the_text, 1, re.DOTALL)
#        after_tag = re.sub(r"(.*?)(<" + the_tag + "(>| [^/>]*).*$)", r"\2", the_text, 1, re.DOTALL)
#        if the_tag == "task":
#          print "++++++++++++++scanning for", the_tag,"tag in",the_text + the_end + ">"
#          print "/////////scanning for"
   #     the_text = before_tag + tag_to_numbered_tag(after_tag + the_end + ">", the_tag)
        the_text = tag_to_numbered_tag(the_tag, the_text + the_end + ">")

        # this is necessary, but not obviously so
        component.something_changed = True
#        if the_tag == "task":
#          print "++++++++++++++now returning", the_start1 + the_start2 + the_text # + the_end + ">"
#          print "///////now returning"
        return the_start1 + the_start2 + the_text  #+ the_end + ">"
    else:
        this_N = component.lipcounter[the_tag]
        component.lipcounter[the_tag] += 1
#        if the_tag == "task":
#             print "++++++++++++++incrementing",tag
#             print the_start1 + str(this_N) + the_start2  + the_text + the_end + str(this_N) + ">"
#             print "-----------------"
        
        return the_start1 + str(this_N) + the_start2  + the_text + the_end + str(this_N) + ">"

