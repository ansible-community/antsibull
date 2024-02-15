# antsibull \-\- Ansible Build Scripts Release Notes

**Topics**
- <a href="#v0-60-0">v0\.60\.0</a>
  - <a href="#release-summary">Release Summary</a>
  - <a href="#minor-changes">Minor Changes</a>
  - <a href="#bugfixes">Bugfixes</a>
- <a href="#v0-59-1">v0\.59\.1</a>
  - <a href="#release-summary-1">Release Summary</a>
  - <a href="#bugfixes-1">Bugfixes</a>
- <a href="#v0-59-0">v0\.59\.0</a>
  - <a href="#release-summary-2">Release Summary</a>
  - <a href="#minor-changes-1">Minor Changes</a>
  - <a href="#bugfixes-2">Bugfixes</a>
- <a href="#v0-58-0">v0\.58\.0</a>
  - <a href="#release-summary-3">Release Summary</a>
  - <a href="#minor-changes-2">Minor Changes</a>
  - <a href="#bugfixes-3">Bugfixes</a>
- <a href="#v0-57-1">v0\.57\.1</a>
  - <a href="#release-summary-4">Release Summary</a>
  - <a href="#bugfixes-4">Bugfixes</a>
- <a href="#v0-57-0">v0\.57\.0</a>
  - <a href="#release-summary-5">Release Summary</a>
  - <a href="#minor-changes-3">Minor Changes</a>
  - <a href="#removed-features-previously-deprecated">Removed Features \(previously deprecated\)</a>
  - <a href="#bugfixes-5">Bugfixes</a>
- <a href="#v0-56-1">v0\.56\.1</a>
  - <a href="#release-summary-6">Release Summary</a>
  - <a href="#bugfixes-6">Bugfixes</a>
- <a href="#v0-56-0">v0\.56\.0</a>
  - <a href="#release-summary-7">Release Summary</a>
  - <a href="#minor-changes-4">Minor Changes</a>
  - <a href="#deprecated-features">Deprecated Features</a>
- <a href="#v0-55-0">v0\.55\.0</a>
  - <a href="#release-summary-8">Release Summary</a>
  - <a href="#major-changes">Major Changes</a>
  - <a href="#minor-changes-5">Minor Changes</a>
  - <a href="#deprecated-features-1">Deprecated Features</a>
- <a href="#v0-54-0">v0\.54\.0</a>
  - <a href="#release-summary-9">Release Summary</a>
  - <a href="#breaking-changes--porting-guide">Breaking Changes / Porting Guide</a>
  - <a href="#removed-features-previously-deprecated-1">Removed Features \(previously deprecated\)</a>
  - <a href="#bugfixes-7">Bugfixes</a>
- <a href="#v0-53-0">v0\.53\.0</a>
  - <a href="#release-summary-10">Release Summary</a>
  - <a href="#minor-changes-6">Minor Changes</a>
  - <a href="#bugfixes-8">Bugfixes</a>
- <a href="#v0-52-0">v0\.52\.0</a>
  - <a href="#release-summary-11">Release Summary</a>
  - <a href="#minor-changes-7">Minor Changes</a>
  - <a href="#breaking-changes--porting-guide-1">Breaking Changes / Porting Guide</a>
  - <a href="#removed-features-previously-deprecated-2">Removed Features \(previously deprecated\)</a>
- <a href="#v0-51-2">v0\.51\.2</a>
  - <a href="#release-summary-12">Release Summary</a>
  - <a href="#bugfixes-9">Bugfixes</a>
- <a href="#v0-51-1">v0\.51\.1</a>
  - <a href="#release-summary-13">Release Summary</a>
  - <a href="#bugfixes-10">Bugfixes</a>
- <a href="#v0-51-0">v0\.51\.0</a>
  - <a href="#release-summary-14">Release Summary</a>
  - <a href="#minor-changes-8">Minor Changes</a>
- <a href="#v0-50-0">v0\.50\.0</a>
  - <a href="#release-summary-15">Release Summary</a>
  - <a href="#minor-changes-9">Minor Changes</a>
  - <a href="#bugfixes-11">Bugfixes</a>
- <a href="#v0-49-0">v0\.49\.0</a>
  - <a href="#release-summary-16">Release Summary</a>
  - <a href="#minor-changes-10">Minor Changes</a>
  - <a href="#breaking-changes--porting-guide-2">Breaking Changes / Porting Guide</a>
  - <a href="#bugfixes-12">Bugfixes</a>
- <a href="#v0-48-0">v0\.48\.0</a>
  - <a href="#release-summary-17">Release Summary</a>
  - <a href="#minor-changes-11">Minor Changes</a>
  - <a href="#breaking-changes--porting-guide-3">Breaking Changes / Porting Guide</a>
  - <a href="#bugfixes-13">Bugfixes</a>
- <a href="#v0-47-0">v0\.47\.0</a>
  - <a href="#release-summary-18">Release Summary</a>
  - <a href="#minor-changes-12">Minor Changes</a>
- <a href="#v0-46-0">v0\.46\.0</a>
  - <a href="#release-summary-19">Release Summary</a>
  - <a href="#minor-changes-13">Minor Changes</a>
  - <a href="#bugfixes-14">Bugfixes</a>
- <a href="#v0-45-1">v0\.45\.1</a>
  - <a href="#release-summary-20">Release Summary</a>
  - <a href="#bugfixes-15">Bugfixes</a>
- <a href="#v0-45-0">v0\.45\.0</a>
  - <a href="#release-summary-21">Release Summary</a>
  - <a href="#minor-changes-14">Minor Changes</a>
  - <a href="#breaking-changes--porting-guide-4">Breaking Changes / Porting Guide</a>
- <a href="#v0-44-0">v0\.44\.0</a>
  - <a href="#release-summary-22">Release Summary</a>
  - <a href="#major-changes-1">Major Changes</a>
  - <a href="#deprecated-features-2">Deprecated Features</a>
  - <a href="#known-issues">Known Issues</a>
- <a href="#v0-43-0">v0\.43\.0</a>
  - <a href="#release-summary-23">Release Summary</a>
  - <a href="#minor-changes-15">Minor Changes</a>
  - <a href="#bugfixes-16">Bugfixes</a>
- <a href="#v0-42-1">v0\.42\.1</a>
  - <a href="#release-summary-24">Release Summary</a>
  - <a href="#bugfixes-17">Bugfixes</a>
- <a href="#v0-42-0">v0\.42\.0</a>
  - <a href="#release-summary-25">Release Summary</a>
  - <a href="#major-changes-2">Major Changes</a>
  - <a href="#minor-changes-16">Minor Changes</a>
  - <a href="#bugfixes-18">Bugfixes</a>
- <a href="#v0-41-0">v0\.41\.0</a>
  - <a href="#release-summary-26">Release Summary</a>
  - <a href="#minor-changes-17">Minor Changes</a>
  - <a href="#bugfixes-19">Bugfixes</a>
- <a href="#v0-40-2">v0\.40\.2</a>
  - <a href="#release-summary-27">Release Summary</a>
  - <a href="#bugfixes-20">Bugfixes</a>
- <a href="#v0-40-1">v0\.40\.1</a>
  - <a href="#release-summary-28">Release Summary</a>
  - <a href="#bugfixes-21">Bugfixes</a>
- <a href="#v0-40-0">v0\.40\.0</a>
  - <a href="#release-summary-29">Release Summary</a>
  - <a href="#major-changes-3">Major Changes</a>
  - <a href="#minor-changes-18">Minor Changes</a>
  - <a href="#deprecated-features-3">Deprecated Features</a>
  - <a href="#bugfixes-22">Bugfixes</a>
- <a href="#v0-39-2">v0\.39\.2</a>
  - <a href="#release-summary-30">Release Summary</a>
- <a href="#v0-39-1">v0\.39\.1</a>
  - <a href="#release-summary-31">Release Summary</a>
- <a href="#v0-39-0">v0\.39\.0</a>
  - <a href="#release-summary-32">Release Summary</a>
- <a href="#v0-38-2">v0\.38\.2</a>
  - <a href="#release-summary-33">Release Summary</a>
- <a href="#v0-38-1">v0\.38\.1</a>
  - <a href="#release-summary-34">Release Summary</a>
- <a href="#v0-38-0">v0\.38\.0</a>
  - <a href="#release-summary-35">Release Summary</a>
- <a href="#v0-37-0">v0\.37\.0</a>
- <a href="#v0-36-0">v0\.36\.0</a>
- <a href="#v0-35-0">v0\.35\.0</a>
- <a href="#v0-34-0">v0\.34\.0</a>
- <a href="#v0-33-0">v0\.33\.0</a>
- <a href="#v0-32-0">v0\.32\.0</a>
- <a href="#v0-31-0">v0\.31\.0</a>
- <a href="#v0-30-0">v0\.30\.0</a>
- <a href="#v0-29-0">v0\.29\.0</a>
- <a href="#v0-28-0">v0\.28\.0</a>
- <a href="#v0-27-0">v0\.27\.0</a>
- <a href="#v0-26-0">v0\.26\.0</a>
- <a href="#v0-25-0">v0\.25\.0</a>
- <a href="#v0-24-0">v0\.24\.0</a>
- <a href="#v0-23-0">v0\.23\.0</a>
- <a href="#v0-22-0">v0\.22\.0</a>
- <a href="#v0-21-0">v0\.21\.0</a>
- <a href="#v0-20-0">v0\.20\.0</a>
- <a href="#v0-19-0">v0\.19\.0</a>
- <a href="#v0-18-0">v0\.18\.0</a>
- <a href="#v0-17-0">v0\.17\.0</a>
- <a href="#v0-16-0">v0\.16\.0</a>
- <a href="#v0-15-0">v0\.15\.0</a>
- <a href="#v0-14-0">v0\.14\.0</a>
- <a href="#v0-13-0">v0\.13\.0</a>
- <a href="#v0-12-0">v0\.12\.0</a>
- <a href="#v0-11-0">v0\.11\.0</a>
- <a href="#v0-10-0">v0\.10\.0</a>
- <a href="#v0-9-0">v0\.9\.0</a>
- <a href="#v0-8-0">v0\.8\.0</a>
- <a href="#v0-7-0">v0\.7\.0</a>
- <a href="#v0-6-0">v0\.6\.0</a>
- <a href="#v0-5-0">v0\.5\.0</a>
- <a href="#v0-4-0">v0\.4\.0</a>
- <a href="#v0-3-0">v0\.3\.0</a>
- <a href="#v0-2-0">v0\.2\.0</a>
- <a href="#v0-1-0">v0\.1\.0</a>
  - <a href="#release-summary-36">Release Summary</a>

<a id="v0-60-0"></a>
## v0\.60\.0

<a id="release-summary"></a>
### Release Summary

Bugfix and feature release

<a id="minor-changes"></a>
### Minor Changes

* Add a <code>sanity\-tests</code> subcommand to run sanity tests accross the collection tree created by <code>verify\-upstreams</code> and display the results \([https\://github\.com/ansible\-community/antsibull/pull/556](https\://github\.com/ansible\-community/antsibull/pull/556)\)\.
* Add a <code>verify\-upstreams</code> subcommand to ensure that files in a collections\' Galaxy collection artifact match its upstream repository \([https\://github\.com/ansible\-community/antsibull/pull/556](https\://github\.com/ansible\-community/antsibull/pull/556)\)\.
* Add new <code>antsibull\-build announcements</code> command to generate release announcement text \([https\://github\.com/ansible\-community/antsibull/pull/573](https\://github\.com/ansible\-community/antsibull/pull/573)\)\.
* Add new <code>antsibull\-build send\-announcements</code> command to interactively send release announcements\. Make sure to install <code>pyperclip</code> with <code>pip install antsibull\[clipboard\]</code> to fully take advantage of its functionality \([https\://github\.com/ansible\-community/antsibull/pull/573](https\://github\.com/ansible\-community/antsibull/pull/573)\)\.
* Add support for the latest antsibull\-core v3 pre\-release\, <code>3\.0\.0a1</code> \([https\://github\.com/ansible\-community/antsibull/pull/586](https\://github\.com/ansible\-community/antsibull/pull/586)\)\.
* Adjust the <code>pip install antsibull</code> call in the <code>build\-ansible\.sh</code> script added to the <code>ansible</code> source distribution to use the version of antsibull used to build the ansible release \([https\://github\.com/ansible\-community/antsibull/pull/563](https\://github\.com/ansible\-community/antsibull/pull/563)\)\.
* Change the license from <code>GPL\-3\.0\-or\-later</code> to <code>GPL\-3\.0\-or\-later AND Python\-2\.0\.1</code>\. Antsibull now contains a small amount of code derived from CPython \([https\://github\.com/ansible\-community/antsibull/pull/556](https\://github\.com/ansible\-community/antsibull/pull/556)\)\.
* Explicitly set up Galaxy context instead of relying on deprecated functionality from antsibull\-core \([https\://github\.com/ansible\-community/antsibull/pull/570](https\://github\.com/ansible\-community/antsibull/pull/570)\)\.
* The Ansible changelog is now generated both in MarkDown and ReStructuredText \([https\://github\.com/ansible\-community/antsibull/pull/576](https\://github\.com/ansible\-community/antsibull/pull/576)\)\.
* The dependency on antsibull\-changelog has been bumped to 0\.24\.0 or later \([https\://github\.com/ansible\-community/antsibull/pull/576](https\://github\.com/ansible\-community/antsibull/pull/576)\)\.
* <code>ansible</code> package README \- add a link to the <code>ansible\-build\-data</code> issue tracker \([https\://github\.com/ansible\-community/antsibull/pull/554](https\://github\.com/ansible\-community/antsibull/pull/554)\)\.

<a id="bugfixes"></a>
### Bugfixes

* Use certain fields from library context instead of app context that are deprecated in the app context and are removed from antsibull\-core 3\.0\.0 \([https\://github\.com/ansible\-community/antsibull/pull/569](https\://github\.com/ansible\-community/antsibull/pull/569)\)\.

<a id="v0-59-1"></a>
## v0\.59\.1

<a id="release-summary-1"></a>
### Release Summary

Hottfix for the ansible 9\.0\.1 release to fix setup\.cfg metadata

<a id="bugfixes-1"></a>
### Bugfixes

* Use the correct directive in <code>setup\.cfg</code> for Ansible 9\+ for requiring a Python version\, i\.e\. use <code>python\_requires</code> instead of <code>requires\_python</code> \([https\://github\.com/ansible\-community/antsibull/pull/559](https\://github\.com/ansible\-community/antsibull/pull/559)\)\.

<a id="v0-59-0"></a>
## v0\.59\.0

<a id="release-summary-2"></a>
### Release Summary

Feature release for the upcoming Ansible 9\.0\.0rc1 release\.

<a id="minor-changes-1"></a>
### Minor Changes

* <code>ansible</code> python metadata \- remove links specific to <code>ansible\-core</code> and add links to the Ansible forum and the <code>ansible\-build\-data</code> repository \([https\://github\.com/ansible\-community/antsibull/pull/558](https\://github\.com/ansible\-community/antsibull/pull/558)\)\.
* build\-release role \- add <code>changed\_when\: false</code> to validate\-tags task \([https\://github\.com/ansible\-community/antsibulll/pull/557](https\://github\.com/ansible\-community/antsibulll/pull/557)\)\.
* build\-release role \- add a test to ensure that Python files in the ansible package successfully compile \([https\://github\.com/ansible\-community/antsibull/pull/552](https\://github\.com/ansible\-community/antsibull/pull/552)\)\.
* build\-release role \- directly install the wheel when running tests \([https\://github\.com/ansible\-community/antsibull/pull/553](https\://github\.com/ansible\-community/antsibull/pull/553)\)\.

<a id="bugfixes-2"></a>
### Bugfixes

* Fix regression in <code>validate\-tags</code> subcommand argument validation that caused a traceback \([https\://github\.com/ansible\-community/antsibull/pull/51](https\://github\.com/ansible\-community/antsibull/pull/51)\)\.

<a id="v0-58-0"></a>
## v0\.58\.0

<a id="release-summary-3"></a>
### Release Summary

Feature release for the upcoming Ansible 9\.0\.0a1 release\.

<a id="minor-changes-2"></a>
### Minor Changes

* Support a constraints file that allows to fix dependencies for the <code>new\-ansible</code> and <code>prepare</code> subcommands \([https\://github\.com/ansible\-community/antsibull/pull/546](https\://github\.com/ansible\-community/antsibull/pull/546)\)\.

<a id="bugfixes-3"></a>
### Bugfixes

* Fix URL to <code>ansible\-core</code> on PyPI in the <code>ansible</code> README \([https\://github\.com/ansible\-collections/overview/issues/228](https\://github\.com/ansible\-collections/overview/issues/228)\, [https\://github\.com/ansible\-community/antsibull/pull/541](https\://github\.com/ansible\-community/antsibull/pull/541)\)\.

<a id="v0-57-1"></a>
## v0\.57\.1

<a id="release-summary-4"></a>
### Release Summary

This bugfix release fixes the retrieval of ansible\-core Porting Guides\.

<a id="bugfixes-4"></a>
### Bugfixes

* Retrieve the ansible\-core Porting Guide from the ansible\-documentation repo\. These files are being removed from the ansible\-core repo \([https\://github\.com/ansible\-community/antsibull/pull/540](https\://github\.com/ansible\-community/antsibull/pull/540)\)\.

<a id="v0-57-0"></a>
## v0\.57\.0

<a id="release-summary-5"></a>
### Release Summary

This release adds a couple new features and drops support for older ansible versions\.

<a id="minor-changes-3"></a>
### Minor Changes

* Antsibull now no longer depends directly on <code>sh</code> \([https\://github\.com/ansible\-community/antsibull/pull/514](https\://github\.com/ansible\-community/antsibull/pull/514)\)\.
* Antsibull now uses <code>sys\.executable</code> instead of the first <code>\'python\'</code> in <code>\$PATH</code> to call the PyPA build tool \([https\://github\.com/ansible\-community/antsibull/pull/514](https\://github\.com/ansible\-community/antsibull/pull/514)\)\.
* Make <code>dep\_closure</code> errors clearer by including the offending collection\'s version in the message \([https\://github\.com/ansible\-community/antsibull/pull/531](https\://github\.com/ansible\-community/antsibull/pull/531)\)\.
* Move setuptools configuration into the declarative <code>setup\.cfg</code> format for Ansible 9 and above\. <code>ansible</code> sdists will still contain a <code>setup\.py</code> file\, but we recommend that users move to tools like <code>pip</code> and <code>build</code> and the PEP 517 interface instead of setuptools\' deprecated <code>setup\.py</code> interface \([https\://github\.com/ansible\-community/antsibull/pull/530](https\://github\.com/ansible\-community/antsibull/pull/530)\)\.
* Now depends antsibull\-core 2\.0\.0 or newer\; antsibull\-core 1\.x\.y is no longer supported \([https\://github\.com/ansible\-community/antsibull/pull/514](https\://github\.com/ansible\-community/antsibull/pull/514)\)\.
* release playbook \- run <code>antsibull\-build validate\-tags\-file</code> to ensure that collections follow the Release Management section of the Collection Requirements \([https\://github\.com/ansible\-community/antsibull/pull/518](https\://github\.com/ansible\-community/antsibull/pull/518)\)\.

<a id="removed-features-previously-deprecated"></a>
### Removed Features \(previously deprecated\)

* Remove code to build ansible versions \< 6\.0\.0 from the <code>setup\.py</code> template and elsewhere in the codebase\. <code>antsibull\-build</code> will error out if a user attempts to build an unsupported version \([https\://github\.com/ansible\-community/antsibull/pull/477](https\://github\.com/ansible\-community/antsibull/pull/477)\, [https\://github\.com/ansible\-community/antsibull/pull/524](https\://github\.com/ansible\-community/antsibull/pull/524)\)\.
* Removed the deprecated <code>multiple</code> and <code>collection</code> subcommands \([https\://github\.com/ansible\-community/antsibull/issues/522](https\://github\.com/ansible\-community/antsibull/issues/522)\, [https\://github\.com/ansible\-community/antsibull/pull/525](https\://github\.com/ansible\-community/antsibull/pull/525)\)\.

<a id="bugfixes-5"></a>
### Bugfixes

* Properly handle non\-standard version ranges or version pins for feature freeze \([https\://github\.com/ansible\-community/antsibull/issues/532](https\://github\.com/ansible\-community/antsibull/issues/532)\, [https\://github\.com/ansible\-community/antsibull/pull/533](https\://github\.com/ansible\-community/antsibull/pull/533)\)\.

<a id="v0-56-1"></a>
## v0\.56\.1

<a id="release-summary-6"></a>
### Release Summary

Hotfix release to fix compatibility with older setuptools versions

<a id="bugfixes-6"></a>
### Bugfixes

* For <code>setup\.py</code> generated for Ansible 8\+\, do not use recursive globs \(<code>\*\*</code>\) as these are only supported since setuptools 62\.3\.0 \([https\://github\.com/ansible\-community/antsibull/pull/520](https\://github\.com/ansible\-community/antsibull/pull/520)\)\.

<a id="v0-56-0"></a>
## v0\.56\.0

<a id="release-summary-7"></a>
### Release Summary

Maintenance release\.

<a id="minor-changes-4"></a>
### Minor Changes

* Remove now broken self\-test from release role \([https\://github\.com/ansible\-community/antsibull/pull/512](https\://github\.com/ansible\-community/antsibull/pull/512)\)\.
* Remove the parameters <code>antsibull\_ansible\_git\_repo</code>\, <code>antsibull\_ansible\_git\_version</code>\, and <code>antsibull\_ansible\_git\_dir</code> from release role \([https\://github\.com/ansible\-community/antsibull/pull/512](https\://github\.com/ansible\-community/antsibull/pull/512)\)\.

<a id="deprecated-features"></a>
### Deprecated Features

* Support for building ansible major versions less than 6 is deprecated and will be removed in an upcoming release \([https\://github\.com/ansible\-community/antsibull/pull/515](https\://github\.com/ansible\-community/antsibull/pull/515)\)\.

<a id="v0-55-0"></a>
## v0\.55\.0

<a id="release-summary-8"></a>
### Release Summary

Release with new features\, other improvements\, a new build system\, and a deprecation

<a id="major-changes"></a>
### Major Changes

* Change pyproject build backend from <code>poetry\-core</code> to <code>hatchling</code>\. <code>pip install antsibull</code> works exactly the same as before\, but some users may be affected depending on how they build/install the project \([https\://github\.com/ansible\-community/antsibull/pull/490](https\://github\.com/ansible\-community/antsibull/pull/490)\)\.

<a id="minor-changes-5"></a>
### Minor Changes

* Add a <code>\-I</code> / <code>\-\-ignore</code> and a <code>\-\-ignores\-file</code> flag to the <code>antsibull\-build validate\-tags</code> and <code>antsibull\-build validate\-tags\-file</code> subcommands to ignore errors for certain collections \([https\://github\.com/ansible\-community/antsibull/pull/491](https\://github\.com/ansible\-community/antsibull/pull/491)\)\.
* Make compatible with deprecations issued by newer setuptools releases \([https\://github\.com/ansible\-community/antsibull/issues/433](https\://github\.com/ansible\-community/antsibull/issues/433)\, [https\://github\.com/ansible\-community/antsibull/pull/502](https\://github\.com/ansible\-community/antsibull/pull/502)\)\.
* Use the pypa <code>build</code> tool to build wheels and source distributions for ansible in an isolated environment\. This replaces direct calls to <code>python setup\.py bdist\_wheel</code> and <code>python setup\.py sdist</code> which are deprecated \([https\://github\.com/ansible\-community/antsibull/pull/492](https\://github\.com/ansible\-community/antsibull/pull/492)\)\.

<a id="deprecated-features-1"></a>
### Deprecated Features

* The <code>multiple</code> and <code>collection</code> subcommands are deprecated and will be removed soon\. They were never used to our knowledge except in the exploratory phase before the first Ansible 2\.10 releases\, have no test coverage\, and might not even work at all\. If you are actively using them and are interested in keeping them\, please create an issue in the antsibull repository as soon as possible \([https\://github\.com/ansible\-community/antsibull/pull/505](https\://github\.com/ansible\-community/antsibull/pull/505)\)\.

<a id="v0-54-0"></a>
## v0\.54\.0

<a id="release-summary-9"></a>
### Release Summary

New release with features\, bugfixes\, and breaking changes\.

<a id="breaking-changes--porting-guide"></a>
### Breaking Changes / Porting Guide

* Drop support for Python 3\.8 \([https\://github\.com/ansible\-community/antsibull/pull/465](https\://github\.com/ansible\-community/antsibull/pull/465)\)\.

<a id="removed-features-previously-deprecated-1"></a>
### Removed Features \(previously deprecated\)

* Removed the <code>antsibull\-lint</code> command line utility\. It had no functionality anymore for some time now \([https\://github\.com/ansible\-community/antsibull/pull/466](https\://github\.com/ansible\-community/antsibull/pull/466)\)\.

<a id="bugfixes-7"></a>
### Bugfixes

* Explicitly declare the <code>sh</code> dependency and limit it to before 2\.0\.0\. Also explicitly declare the dependencies on <code>packaging</code>\, <code>semantic\_version</code>\, <code>aiofiles</code>\, <code>aiohttp</code>\, and <code>twiggy</code> \([https\://github\.com/ansible\-community/antsibull/pull/487](https\://github\.com/ansible\-community/antsibull/pull/487)\)\.
* Fix broken ansible\-build\-data repository link in ansible package README \([https\://github\.com/ansible\-community/antsibull/pull/485](https\://github\.com/ansible\-community/antsibull/pull/485)\)\.

<a id="v0-53-0"></a>
## v0\.53\.0

<a id="release-summary-10"></a>
### Release Summary

Feature and bugfix release\.

<a id="minor-changes-6"></a>
### Minor Changes

* Add <code>\-\-tags\-file</code> option to the <code>single</code>\, <code>rebuild\-single</code>\, and <code>prepare</code> subcommands\. This allows including a collection git tags data file in ansible\-build\-data and the ansible sdist \([https\://github\.com/ansible\-community/antsibull/pull/476/](https\://github\.com/ansible\-community/antsibull/pull/476/)\)\.
* Add <code>pyproject\.toml</code> to ansible sdist to use the <code>setuptools\.build\_meta</code> [PEP 517](https\://peps\.python\.org/pep\-0517/) backend\. Tools that still call <code>setup\.py</code> directly will work the same as they did before \([https\://github\.com/ansible\-community/antsibull/pull/471](https\://github\.com/ansible\-community/antsibull/pull/471)\)\.
* Bump minimum <code>antsibull\-core</code> requirement to 1\.5\.0\. It contains changes that are needed for the new <code>\-\-tags\-file</code> option \([https\://github\.com/ansible\-community/antsibull/pull/476/](https\://github\.com/ansible\-community/antsibull/pull/476/)\)\.
* There have been internal refactorings to simplify typing \([https\://github\.com/ansible\-community/antsibull/pull/469](https\://github\.com/ansible\-community/antsibull/pull/469)\)\.

<a id="bugfixes-8"></a>
### Bugfixes

* Correct Python version classifiers in the ansible <code>setup\.py</code> template\. Limit the Python 3\.8 classifer to ansible 5 and 6 and add the Python 3\.11 classifier to ansible \>\= 7 \([https\://github\.com/ansible\-community/antsibull/pull/479](https\://github\.com/ansible\-community/antsibull/pull/479)\)\.
* Do not crash when the <code>changelogs/changelog\.yaml</code> file of a collection cannot be loaded \([https\://github\.com/ansible\-community/antsibull/issues/481](https\://github\.com/ansible\-community/antsibull/issues/481)\, [https\://github\.com/ansible\-community/antsibull/pull/482](https\://github\.com/ansible\-community/antsibull/pull/482)\)\.

<a id="v0-52-0"></a>
## v0\.52\.0

<a id="release-summary-11"></a>
### Release Summary

Major feature and bugfix release with breaking changes\.

<a id="minor-changes-7"></a>
### Minor Changes

* Add a <code>validate\-tags</code> subcommand to ensure that collection versions in an Ansible release are tagged in collections\' respective git repositories \([https\://github\.com/ansible\-community/antsibull/pull/456](https\://github\.com/ansible\-community/antsibull/pull/456)\)\.
* Make compatible with antsibull\-core 2\.x\.y \([https\://github\.com/ansible\-community/antsibull/pull/463](https\://github\.com/ansible\-community/antsibull/pull/463)\)\.

<a id="breaking-changes--porting-guide-1"></a>
### Breaking Changes / Porting Guide

* Drops support for Python 3\.6 an 3\.7 \([https\://github\.com/ansible\-community/antsibull/issues/458](https\://github\.com/ansible\-community/antsibull/issues/458)\, [https\://github\.com/ansible\-community/antsibull/pull/460](https\://github\.com/ansible\-community/antsibull/pull/460)\)\.
* The antsibull\-docs dependency has been removed \([https\://github\.com/ansible\-community/antsibull/pull/451](https\://github\.com/ansible\-community/antsibull/pull/451)\)\.

<a id="removed-features-previously-deprecated-2"></a>
### Removed Features \(previously deprecated\)

* The deprecated <code>antsibull\-lint</code> subcommands have been removed\. Use <code>antsibull\-changelog lint\-changelog\-yaml</code> or <code>antsibull\-docs lint\-collection\-docs</code> depending on your use\-case \([https\://github\.com/ansible\-community/antsibull/pull/451](https\://github\.com/ansible\-community/antsibull/pull/451)\)\.
* The deprecated <code>build\-collection</code> subcommand of <code>antsibull\-build</code> has been removed\. Use <code>collection</code> instead \([https\://github\.com/ansible\-community/antsibull/pull/451](https\://github\.com/ansible\-community/antsibull/pull/451)\)\.
* The deprecated <code>build\-multiple</code> subcommand of <code>antsibull\-build</code> has been removed\. Use <code>multiple</code> instead \([https\://github\.com/ansible\-community/antsibull/pull/451](https\://github\.com/ansible\-community/antsibull/pull/451)\)\.
* The deprecated <code>build\-single</code> subcommand of <code>antsibull\-build</code> has been removed\. Use <code>single</code> instead \([https\://github\.com/ansible\-community/antsibull/pull/451](https\://github\.com/ansible\-community/antsibull/pull/451)\)\.
* The deprecated <code>new\-acd</code> subcommand of <code>antsibull\-build</code> has been removed\. Use <code>new\-ansible</code> instead \([https\://github\.com/ansible\-community/antsibull/pull/451](https\://github\.com/ansible\-community/antsibull/pull/451)\)\.

<a id="v0-51-2"></a>
## v0\.51\.2

<a id="release-summary-12"></a>
### Release Summary

Bugfix release\. The next minor release will no longer support Python 3\.6 and 3\.7\.

<a id="bugfixes-9"></a>
### Bugfixes

* Add <code>\-\-collection\-dir</code> to the <code>antsibull\-build</code> <code>collection</code> and <code>build\-collection</code> subcommands\. Previously\, the <code>\-\-collection\-dir</code> option was added to the wrong CLI argument parser and not exposed to users\. \([https\://github\.com/ansible\-community/antsibull/pull/461](https\://github\.com/ansible\-community/antsibull/pull/461)\)\.
* Use compatibility code instead of trying to run <code>asyncio\.run</code> directly\, which will fail with Python 3\.6 \([https\://github\.com/ansible\-community/antsibull/pull/459](https\://github\.com/ansible\-community/antsibull/pull/459)\)\.

<a id="v0-51-1"></a>
## v0\.51\.1

<a id="release-summary-13"></a>
### Release Summary

Bugfix release\.

<a id="bugfixes-10"></a>
### Bugfixes

* Fix handling of Python dependency data when building changelogs and collections \([https\://github\.com/ansible\-community/antsibull/pull/452](https\://github\.com/ansible\-community/antsibull/pull/452)\)\.

<a id="v0-51-0"></a>
## v0\.51\.0

<a id="release-summary-14"></a>
### Release Summary

Feature release for Ansible 7\.

<a id="minor-changes-8"></a>
### Minor Changes

* Now requires antsibull\-core \>\= 1\.3\.0 \([https\://github\.com/ansible\-community/antsibull/pull/449](https\://github\.com/ansible\-community/antsibull/pull/449)\)\.
* The <code>python\_requires</code> information is now extracted from ansible\-core and stored in the <code>\.build</code> and <code>\.deps</code> files instead of guessing it from the Ansible version \([https\://github\.com/ansible\-community/antsibull/pull/449](https\://github\.com/ansible\-community/antsibull/pull/449)\)\.

<a id="v0-50-0"></a>
## v0\.50\.0

<a id="release-summary-15"></a>
### Release Summary

Feature and bugfix release\.

<a id="minor-changes-9"></a>
### Minor Changes

* Added galaxy <code>requirements\.yml</code> file as <code>build\-release</code> role depends on <code>community\.general</code> collection \([https\://github\.com/ansible\-community/antsibull/pull/432](https\://github\.com/ansible\-community/antsibull/pull/432)\)
* Define minimal Python requirement for Ansible X depending on X\, under the assumption that ansible\-core\'s Python requirement is increased by one version every two ansible\-core major releases\, and that every Ansible major release corresponds to an ansible\-core major release from Ansible 5 on \([https\://github\.com/ansible\-community/antsibull/pull/448](https\://github\.com/ansible\-community/antsibull/pull/448)\)\.
* The <code>build\-release</code> role fails to execute when <code>\./build/antsibull\-build\-data</code> doesn\'t exist and when the <code>antsibull\_data\_reset</code> variable is set to <code>false</code> \([https\://github\.com/ansible\-community/antsibull/pull/442](https\://github\.com/ansible\-community/antsibull/pull/442)\)\.
* When building Ansible 6\.3\.0 or newer\, fail on collection dependency validations \([https\://github\.com/ansible\-community/community\-topics/issues/94](https\://github\.com/ansible\-community/community\-topics/issues/94)\, [https\://github\.com/ansible\-community/antsibull/pull/440](https\://github\.com/ansible\-community/antsibull/pull/440)\)\.

<a id="bugfixes-11"></a>
### Bugfixes

* Adjust release role to work around a bug in the current beta version of ansible\-core 2\.14 \([https\://github\.com/ansible\-community/antsibull/pull/447](https\://github\.com/ansible\-community/antsibull/pull/447)\)\.
* Fix typing errors in the <code>multiple</code> subcommand \([https\://github\.com/ansible\-community/antsibull/pull/443](https\://github\.com/ansible\-community/antsibull/pull/443)\)\.

<a id="v0-49-0"></a>
## v0\.49\.0

<a id="release-summary-16"></a>
### Release Summary

Bugfix and feature release containing breaking changes in the release role\.

<a id="minor-changes-10"></a>
### Minor Changes

* Allow to copy the files used to create the source distribution and wheels to a new directory during <code>antsibull\-build rebuild\-single</code> \([https\://github\.com/ansible\-community/antsibull/pull/435](https\://github\.com/ansible\-community/antsibull/pull/435)\)\.
* Perform minor refactoring of the <code>build\-release</code> role\, mostly concerning <code>tasks/tests\.yml</code>\. This reduces use of <code>shell</code> and <code>set\_fact</code>\, makes the role more robust\, and replaces short names with FQCNs \([https\://github\.com/ansible\-community/antsibull/pull/432](https\://github\.com/ansible\-community/antsibull/pull/432)\)\.
* Show warnings emitted by building the source distribution and/or wheels \([https\://github\.com/ansible\-community/antsibull/pull/435](https\://github\.com/ansible\-community/antsibull/pull/435)\)\.
* The files in the source repository now follow the [REUSE Specification](https\://reuse\.software/spec/)\. The only exceptions are changelog fragments in <code>changelogs/fragments/</code> \([https\://github\.com/ansible\-community/antsibull/pull/437](https\://github\.com/ansible\-community/antsibull/pull/437)\)\.

<a id="breaking-changes--porting-guide-2"></a>
### Breaking Changes / Porting Guide

* The <code>build\-release</code> role now depends on the <code>community\.general</code> collection \([https\://github\.com/ansible\-community/antsibull/pull/432](https\://github\.com/ansible\-community/antsibull/pull/432)\)\.

<a id="bugfixes-12"></a>
### Bugfixes

* Fix typo in generated MANIFEST\.in to list the existing file <code>README\.rst</code> instead of the non\-existing file <code>README</code> \([https\://github\.com/ansible\-community/antsibull/pull/435](https\://github\.com/ansible\-community/antsibull/pull/435)\)\.
* When preparing a new Ansible release\, only use pre\-releases for ansible\-core when the Ansible release itself is an alpha pre\-release\. This encodes that the first beta release of a new major Ansible release coincides with the ansible\-core GA \([https\://github\.com/ansible\-community/antsibull/pull/436](https\://github\.com/ansible\-community/antsibull/pull/436)\)\.

<a id="v0-48-0"></a>
## v0\.48\.0

<a id="release-summary-17"></a>
### Release Summary

Bugfix and feature release containing some breaking changes in the release role\.

<a id="minor-changes-11"></a>
### Minor Changes

* In the release role\, automatically set <code>antsibull\_build\_file</code> and <code>antsibull\_data\_dir</code> based on <code>antsibull\_ansible\_version</code> \([https\://github\.com/ansible\-community/antsibull/pull/430](https\://github\.com/ansible\-community/antsibull/pull/430)\)\.
* The release role has now an argument spec \([https\://github\.com/ansible\-community/antsibull/pull/430](https\://github\.com/ansible\-community/antsibull/pull/430)\)\.

<a id="breaking-changes--porting-guide-3"></a>
### Breaking Changes / Porting Guide

* In the release role\, <code>antsibull\_ansible\_version</code> and <code>antsibull\_ansible\_git\_version</code> must now always be specified \([https\://github\.com/ansible\-community/antsibull/pull/430](https\://github\.com/ansible\-community/antsibull/pull/430)\)\.

<a id="bugfixes-13"></a>
### Bugfixes

* When preparing a new Ansible release\, bump the ansible\-core version to the latest bugfix version \([https\://github\.com/ansible\-community/antsibull/pull/430](https\://github\.com/ansible\-community/antsibull/pull/430)\)\.

<a id="v0-47-0"></a>
## v0\.47\.0

<a id="release-summary-18"></a>
### Release Summary

Feature release for Ansible 6\.0\.0rc1\.

<a id="minor-changes-12"></a>
### Minor Changes

* Include <code>ansible\-community</code> CLI program with <code>\-\-version</code> parameter from Ansible 6\.0\.0rc1 on \([https\://github\.com/ansible\-community/antsibull/pull/429](https\://github\.com/ansible\-community/antsibull/pull/429)\)\.

<a id="v0-46-0"></a>
## v0\.46\.0

<a id="release-summary-19"></a>
### Release Summary

Feature and bugfix release with improvements for the release role\, release building\, and changelog generation\.

<a id="minor-changes-13"></a>
### Minor Changes

* Avoid including the complete condensed changelog of collections added to Ansible to that Ansible release\'s changelog and porting guide entries \([https\://github\.com/ansible\-community/antsibull/pull/428](https\://github\.com/ansible\-community/antsibull/pull/428)\)\.
* The <code>build\-release</code> role now also uses <code>antsibull\_data\_reset</code> to prevent regeneration of <code>build\-X\.ansible</code> for alpha and beta\-1 releases \([https\://github\.com/ansible\-community/antsibull/pull/422](https\://github\.com/ansible\-community/antsibull/pull/422)\)\.

<a id="bugfixes-14"></a>
### Bugfixes

* In the build\-release role\, when <code>antsibull\_force\_rebuild</code> is true\, delete the existing python wheel in addition to the release tarball \([https\://github\.com/ansible\-community/antsibull/pull/427](https\://github\.com/ansible\-community/antsibull/pull/427)\)\.
* Remove various empty lines from generated <code>setup\.py</code> \([https\://github\.com/ansible\-community/antsibull/issues/424](https\://github\.com/ansible\-community/antsibull/issues/424)\, [https\://github\.com/ansible\-community/antsibull/pull/425](https\://github\.com/ansible\-community/antsibull/pull/425)\)\.
* Use <code>packaging\.version</code> instead of \(indirectly\) <code>distutils\.version</code> to check whether the correct ansible\-core version is installed \([https\://github\.com/ansible\-community/antsibull/pull/426](https\://github\.com/ansible\-community/antsibull/pull/426)\)\.

<a id="v0-45-1"></a>
## v0\.45\.1

<a id="release-summary-20"></a>
### Release Summary

Bugfix release\.

<a id="bugfixes-15"></a>
### Bugfixes

* The <code>build\-release</code> role now no longer ignores collection prereleases of collections for the alpha releases \([https\://github\.com/ansible\-community/antsibull/pull/420](https\://github\.com/ansible\-community/antsibull/pull/420)\)\.

<a id="v0-45-0"></a>
## v0\.45\.0

<a id="release-summary-21"></a>
### Release Summary

New feature release with one breaking change to the <code>build\-release</code> role\.

<a id="minor-changes-14"></a>
### Minor Changes

* Add <code>antsibull\-build</code> subcommand <code>validate\-deps</code> which validates dependencies for an <code>ansible\_collections</code> tree \([https\://github\.com/ansible\-community/antsibull/pull/416](https\://github\.com/ansible\-community/antsibull/pull/416)\)\.
* Check collection dependencies during <code>antsibull\-build rebuild\-single</code> and warn about errors \([https\://github\.com/ansible\-community/antsibull/pull/416](https\://github\.com/ansible\-community/antsibull/pull/416)\)\.
* In the <code>build\-release</code> role\, stop shipping a separate <code>roles/build\-release/files/deps\-to\-galaxy\.py</code> script and use the new galaxy\-requirements\.yaml style file created during release preparation \([https\://github\.com/ansible\-community/antsibull/pull/417](https\://github\.com/ansible\-community/antsibull/pull/417)\)\.
* Update Ansible\'s <code>README\.rst</code> to focus on Ansible package details \([https\://github\.com/ansible\-community/antsibull/pull/415](https\://github\.com/ansible\-community/antsibull/pull/415)\)\.
* When preparing a new Ansible release with <code>antsibull\-build prepare</code> or <code>antsibull\-build single</code>\, create a galaxy\-requirements\.yaml style file next to the dependencies file \([https\://github\.com/ansible\-community/antsibull/pull/417](https\://github\.com/ansible\-community/antsibull/pull/417)\)\.

<a id="breaking-changes--porting-guide-4"></a>
### Breaking Changes / Porting Guide

* The <code>build\-release</code> role no longer uses poetry to run antsibull\, but assumes that antsibull is installed\. To revert to the old behavior\, set the Ansible variable <code>antsibull\_build\_command</code> to <code>poetry run antsibull</code> \([https\://github\.com/ansible\-community/antsibull/pull/420](https\://github\.com/ansible\-community/antsibull/pull/420)\)\.

<a id="v0-44-0"></a>
## v0\.44\.0

<a id="release-summary-22"></a>
### Release Summary

Split up antsibull into multiple PyPi packages \(<code>antsibull\-core</code>\, <code>antsibull\-docs</code>\, and <code>antsibull</code>\)\. <strong>Note</strong> that upgrading is a bit more complicated due to the way <code>pip</code> works\! See below for details\.

<a id="major-changes-1"></a>
### Major Changes

* The <code>antsibull</code> package now depends on <code>antsibull\-core</code> and <code>antsibull\-docs</code>\, and most code was moved to these two packages\. The <code>antsibull\-docs</code> CLI tool is now part of the <code>antsibull\-docs</code> package as well\. The behavior of the new version should be identical to the previous version \([https\://github\.com/ansible\-community/antsibull/pull/414](https\://github\.com/ansible\-community/antsibull/pull/414)\)\.

<a id="deprecated-features-2"></a>
### Deprecated Features

* The antsibull\-lint command is deprecated\. Use <code>antsibull\-changelog lint\-changelog\-yaml</code> instead of <code>antsibull\-lint changelog\-yaml</code>\, and use <code>antsibull\-docs lint\-collection\-docs</code> instead of <code>antsibull\-lint collection\-docs</code> \([https\://github\.com/ansible\-community/antsibull/pull/412](https\://github\.com/ansible\-community/antsibull/pull/412)\, [https\://github\.com/ansible\-community/antsibull/issues/410](https\://github\.com/ansible\-community/antsibull/issues/410)\)\.

<a id="known-issues"></a>
### Known Issues

* When upgrading from antsibull \< 0\.44\.0 to antsibull 0\.44\.0\+\, it could happen that the <code>antsibull\-docs</code> binary is removed due to how pip works\. To make sure the <code>antsibull\-docs</code> binary is present\, either first uninstall \(<code>pip uninstall antsibull</code>\) before installing the latest antsibull version\, or re\-install <code>antsibull\-docs</code> once the installation finished \(<code>pip install \-\-force\-reinstall antsibull\-docs</code>\) \([https\://github\.com/ansible\-community/antsibull/pull/414](https\://github\.com/ansible\-community/antsibull/pull/414)\)\.

<a id="v0-43-0"></a>
## v0\.43\.0

<a id="release-summary-23"></a>
### Release Summary

Feature release\.

<a id="minor-changes-15"></a>
### Minor Changes

* Add <code>lint\-collection\-docs</code> subcommand to <code>antsibull\-docs</code>\. It behaves identical to <code>antsibull\-lint collection\-docs</code> \([https\://github\.com/ansible\-community/antsibull/pull/411](https\://github\.com/ansible\-community/antsibull/pull/411)\, [https\://github\.com/ansible\-community/antsibull/issues/410](https\://github\.com/ansible\-community/antsibull/issues/410)\)\.
* Support <code>MANIFEST\.json</code> and not only <code>galaxy\.yml</code> for <code>antsibull\-docs lint\-collection\-docs</code> and <code>antsibull\-lint collection\-docs</code> \([https\://github\.com/ansible\-community/antsibull/pull/411](https\://github\.com/ansible\-community/antsibull/pull/411)\)\.

<a id="bugfixes-16"></a>
### Bugfixes

* Prevent crashing when non\-strings are found for certain pathnames for <code>antsibull\-docs lint\-collection\-docs</code> and <code>antsibull\-lint collection\-docs</code> \([https\://github\.com/ansible\-community/antsibull/pull/411](https\://github\.com/ansible\-community/antsibull/pull/411)\)\.

<a id="v0-42-1"></a>
## v0\.42\.1

<a id="release-summary-24"></a>
### Release Summary

Bugfix release\.

<a id="bugfixes-17"></a>
### Bugfixes

* antsibull\-docs sphinx\-init \- the <code>\-\-fail\-on\-error</code> option resulted in an invalid <code>build\.sh</code> \([https\://github\.com/ansible\-community/antsibull/pull/409](https\://github\.com/ansible\-community/antsibull/pull/409)\)\.

<a id="v0-42-0"></a>
## v0\.42\.0

<a id="release-summary-25"></a>
### Release Summary

Major feature release preparing for Ansible 6\. Also adds support for the new collection links file\, and improves the attributes tables\.

<a id="major-changes-2"></a>
### Major Changes

* Allow collections to specify extra links \([https\://github\.com/ansible\-community/antsibull/pull/355](https\://github\.com/ansible\-community/antsibull/pull/355)\)\.
* Building Ansible 6\+ now builds wheels next to the source tarball \([https\://github\.com/ansible\-community/antsibull/pull/394](https\://github\.com/ansible\-community/antsibull/pull/394)\)\.
* From Ansible 6 on\, improve <code>setup\.py</code> to exclude unnecessary files in the Python distribution \([https\://github\.com/ansible\-community/antsibull/pull/342](https\://github\.com/ansible\-community/antsibull/pull/342)\)\.
* Remove Ansible 2\.9 / ansible\-base 2\.10 checks from <code>setup\.py</code> for Ansible 6 so that we can finally ship wheels\. This change is only active for Ansible 6 \([https\://github\.com/ansible\-community/antsibull/pull/394](https\://github\.com/ansible\-community/antsibull/pull/394)\)\.

<a id="minor-changes-16"></a>
### Minor Changes

* Add a new docs parsing backend <code>ansible\-core\-2\.13</code>\, which supports ansible\-core 2\.13\+ \([https\://github\.com/ansible\-community/antsibull/pull/401](https\://github\.com/ansible\-community/antsibull/pull/401)\)\.
* Add an autodetection <code>auto</code> for the docs parsing backend to select the fastest supported backend\. This is the new default \([https\://github\.com/ansible\-community/antsibull/pull/401](https\://github\.com/ansible\-community/antsibull/pull/401)\)\.
* Add option <code>\-\-no\-semantic\-versioning</code> to <code>antsibull\-lint changelog\-yaml</code> command \([https\://github\.com/ansible\-community/antsibull/pull/405](https\://github\.com/ansible\-community/antsibull/pull/405)\)\.
* Change more references to ansible\-base to ansible\-core in the code \([https\://github\.com/ansible\-community/antsibull/pull/398](https\://github\.com/ansible\-community/antsibull/pull/398)\)\.
* If the role is used to build a non\-alpha or first beta version and the bulid file does not exist\, it is created instead of later failing because it does not exist \([https\://github\.com/ansible\-community/antsibull/pull/408](https\://github\.com/ansible\-community/antsibull/pull/408)\)\.
* Mention the <code>ansible\-core</code> major version in the Ansible porting guide \([https\://github\.com/ansible\-community/antsibull/pull/397](https\://github\.com/ansible\-community/antsibull/pull/397)\)\.
* Redo attributes table using the same structure as the options and return value table\. This improves its look and adds a linking mechanism \([https\://github\.com/ansible\-community/antsibull/pull/401](https\://github\.com/ansible\-community/antsibull/pull/401)\)\.

<a id="bugfixes-18"></a>
### Bugfixes

* Fix ansible\-core version parsing for <code>ansible\-doc</code> docs parsing backend \([https\://github\.com/ansible\-community/antsibull/pull/401](https\://github\.com/ansible\-community/antsibull/pull/401)\)\.
* Fix filename of mentioned ansible\-core porting guide in Ansible\'s porting guide introductionary comment \([https\://github\.com/ansible\-community/antsibull/pull/398](https\://github\.com/ansible\-community/antsibull/pull/398)\)\.
* antsibull\-docs will no longer traceback when it tries to process plugins not found in its own constant but are available in ansible\-core \([https\://github\.com/ansible\-community/antsibull/pull/404](https\://github\.com/ansible\-community/antsibull/pull/404)\)\.

<a id="v0-41-0"></a>
## v0\.41\.0

<a id="release-summary-26"></a>
### Release Summary

Feature and bugfix release\.

<a id="minor-changes-17"></a>
### Minor Changes

* Add <code>\-\-fail\-on\-error</code> to all antsibull\-docs subcommands for usage in CI \([https\://github\.com/ansible\-community/antsibull/pull/393](https\://github\.com/ansible\-community/antsibull/pull/393)\)\.
* Allow to select a different Sphinx theme for <code>antsibull\-docs sphinx\-init</code> with the new <code>\-\-sphinx\-theme</code> option \([https\://github\.com/ansible\-community/antsibull/pull/392](https\://github\.com/ansible\-community/antsibull/pull/392)\)\.
* Fully implement <code>antsibull\-docs collection</code>\. So far <code>\-\-current</code> was required \([https\://github\.com/ansible\-community/antsibull/pull/383](https\://github\.com/ansible\-community/antsibull/pull/383)\)\.
* Mention the plugin type more prominently in the documentation \([https\://github\.com/ansible\-community/antsibull/pull/364](https\://github\.com/ansible\-community/antsibull/pull/364)\)\.
* Remove email addresses and <code>\(\!UNKNOWN\)</code> from plugin and role author names \([https\://github\.com/ansible\-community/antsibull/pull/389](https\://github\.com/ansible\-community/antsibull/pull/389)\)\.
* Support new <code>keyword</code> field in plugin documentations \([https\://github\.com/ansible\-community/antsibull/pull/329](https\://github\.com/ansible\-community/antsibull/pull/329)\)\.
* The <code>conf\.py</code> generated by <code>antsibull\-docs sphinx\-init</code> will be set to try resolving intersphinx references to Ansible\'s <code>devel</code> docs instead of a concrete Ansible version \([https\://github\.com/ansible\-community/antsibull/pull/391](https\://github\.com/ansible\-community/antsibull/pull/391)\)\.

<a id="bugfixes-19"></a>
### Bugfixes

* If plugin parsing fails for <code>antsibull\-docs plugin</code>\, handle this more gracefully \([https\://github\.com/ansible\-community/antsibull/pull/393](https\://github\.com/ansible\-community/antsibull/pull/393)\)\.
* Improve error message when plugin specified for <code>antsibull\-docs plugin</code> cannot be found \([https\://github\.com/ansible\-community/antsibull/pull/383](https\://github\.com/ansible\-community/antsibull/pull/383)\)\.
* When using <code>\-\-use\-html\-blobs</code>\, malformed HTML was generated for parameter aliases \([https\://github\.com/ansible\-community/antsibull/pull/388](https\://github\.com/ansible\-community/antsibull/pull/388)\)\.

<a id="v0-40-2"></a>
## v0\.40\.2

<a id="release-summary-27"></a>
### Release Summary

Bugfix release\.

<a id="bugfixes-20"></a>
### Bugfixes

* Fix <code>rsync</code> call when <code>antsibull\-docs sphinx\-init</code> is used with <code>\-\-squash\-hieararchy</code> \([https\://github\.com/ansible\-community/antsibull/pull/382](https\://github\.com/ansible\-community/antsibull/pull/382)\)\.
* Fix invalid HTML in return value RST tables\. Closing <code>\</div\></code> were missing for a wrapping <code>\<div\></code> of every content cell\, causing problems with some text\-based browsers \([https\://github\.com/ansible\-community/antsibull/issues/386](https\://github\.com/ansible\-community/antsibull/issues/386)\, [https\://github\.com/ansible\-community/antsibull/pull/387](https\://github\.com/ansible\-community/antsibull/pull/387)\)\.
* Work around Python argparse bug by using vendored class for all Python versions until the bug is fixed in argparse\. This makes <code>\-\-help</code> work for all antsibull\-docs subcommands \([https\://github\.com/ansible\-community/antsibull/pull/384](https\://github\.com/ansible\-community/antsibull/pull/384)\)\.

<a id="v0-40-1"></a>
## v0\.40\.1

<a id="release-summary-28"></a>
### Release Summary

Bugfix release\.

<a id="bugfixes-21"></a>
### Bugfixes

* Fix bug in collection enum for docs generation\, which caused role FQCNs to be mangled \([https\://github\.com/ansible\-community/antsibull/pull/379](https\://github\.com/ansible\-community/antsibull/pull/379)\)\.

<a id="v0-40-0"></a>
## v0\.40\.0

<a id="release-summary-29"></a>
### Release Summary

Feature and bugfix release\.

<a id="major-changes-3"></a>
### Major Changes

* Responsive parameter and return value tables\. Also use RST tables instead of HTML blobs \([https\://github\.com/ansible\-community/antsibull/pull/335](https\://github\.com/ansible\-community/antsibull/pull/335)\)\.

<a id="minor-changes-18"></a>
### Minor Changes

* Add a changelog \([https\://github\.com/ansible\-community/antsibull/pull/378](https\://github\.com/ansible\-community/antsibull/pull/378)\)\.
* Allow to specify <code>collection\_cache</code> in config file \([https\://github\.com/ansible\-community/antsibull/pull/375](https\://github\.com/ansible\-community/antsibull/pull/375)\)\.
* Allow to still use HTML blobs for parameter and return value tables\. This can be controlled by a CLI option <code>\-\-use\-html\-blobs</code> and by a global config option <code>use\_html\_blobs</code> \([https\://github\.com/ansible\-community/antsibull/pull/360](https\://github\.com/ansible\-community/antsibull/pull/360)\)\.
* Avoid prereleases when creating the <code>\.build</code> file in <code>antsibull\-build new\-acd</code>\. The old behavior of including them can be obtained by passing the <code>\-\-allow\-prereleases</code> option \([https\://github\.com/ansible\-community/antsibull/pull/298](https\://github\.com/ansible\-community/antsibull/pull/298)\)\.
* Change ansible\-base references in documentation and code to ansible\-core where it makes sense \([https\://github\.com/ansible\-community/antsibull/pull/353](https\://github\.com/ansible\-community/antsibull/pull/353)\)\.
* During docs build\, only write/copy files to the destination that have changed assuming they are not too large \([https\://github\.com/ansible\-community/antsibull/pull/374](https\://github\.com/ansible\-community/antsibull/pull/374)\)\.
* Improve <code>build\-ansible\.sh</code> script integrated in the release tarball \([https\://github\.com/ansible\-community/antsibull/pull/369](https\://github\.com/ansible\-community/antsibull/pull/369)\)\.
* Improve <code>galaxy\-requirements\.yaml</code> generation \([https\://github\.com/ansible\-community/antsibull/pull/350](https\://github\.com/ansible\-community/antsibull/pull/350)\)\.
* Mention new options in the porting guide \([https\://github\.com/ansible\-community/antsibull/pull/363](https\://github\.com/ansible\-community/antsibull/pull/363)\)\.
* Modify <code>thread\_max</code> default value from 80 to 8 \([https\://github\.com/ansible\-community/antsibull/pull/365](https\://github\.com/ansible\-community/antsibull/pull/365)\, [https\://github\.com/ansible\-community/antsibull/pull/370](https\://github\.com/ansible\-community/antsibull/pull/370)\)\.
* Move modules to beginning of plugin index \([https\://github\.com/ansible\-community/antsibull/pull/336](https\://github\.com/ansible\-community/antsibull/pull/336)\)\.
* Remove unnecessary Python 2 boilerplates \([https\://github\.com/ansible\-community/antsibull/pull/371](https\://github\.com/ansible\-community/antsibull/pull/371)\)\.
* Simplify ansible\-core dependency in <code>setup\.py</code> with compatibility operator \([https\://github\.com/ansible\-community/antsibull/pull/346](https\://github\.com/ansible\-community/antsibull/pull/346)\)\.
* Split <code>antsibull\-build single</code> subcommand into <code>prepare</code> and <code>rebuild\-single</code> subcommand \([https\://github\.com/ansible\-community/antsibull/pull/341](https\://github\.com/ansible\-community/antsibull/pull/341)\)\.
* Stop using deprecated Python standard library <code>distutils\.version</code> \([https\://github\.com/ansible\-community/antsibull/pull/372](https\://github\.com/ansible\-community/antsibull/pull/372)\)\.
* Various improvements to the build role \([https\://github\.com/ansible\-community/antsibull/pull/338](https\://github\.com/ansible\-community/antsibull/pull/338)\)\.

<a id="deprecated-features-3"></a>
### Deprecated Features

* The <code>antsibull\-build single</code> subcommand is deprecated\. Use the <code>prepare</code> and <code>rebuild\-single</code> subcommands instead \([https\://github\.com/ansible\-community/antsibull/pull/341](https\://github\.com/ansible\-community/antsibull/pull/341)\)\.

<a id="bugfixes-22"></a>
### Bugfixes

* Fix <code>rsync</code> flags in build scripts generated by <code>antsibull\-docs sphinx\-init</code> to allow Sphinx to not rebuild unchanged files \([https\://github\.com/ansible\-community/antsibull/pull/357](https\://github\.com/ansible\-community/antsibull/pull/357)\)\.
* Fix boolean logic error when <code>\-\-skip\-indexes</code> was used in <code>antsibull\-docs</code> \([https\://github\.com/ansible\-community/antsibull/pull/377](https\://github\.com/ansible\-community/antsibull/pull/377)\)\.
* Fix feature freeze handling after Beta 1 in build role \([https\://github\.com/ansible\-community/antsibull/pull/337](https\://github\.com/ansible\-community/antsibull/pull/337)\)\.
* Require Python 3\.8 for Ansible 5 \([https\://github\.com/ansible\-community/antsibull/pull/345](https\://github\.com/ansible\-community/antsibull/pull/345)\)\.

<a id="v0-39-2"></a>
## v0\.39\.2

<a id="release-summary-30"></a>
### Release Summary

- Fixes an incompatibility with antsibull\-lint with Python 3\.9\.8\.
- Improves and extends the Ansible build role and its tests\.

<a id="v0-39-1"></a>
## v0\.39\.1

<a id="release-summary-31"></a>
### Release Summary

- Fixes <code>M\(\.\.\.\)</code> when used in HTML blobs\.
- Improve wait on HTTP retries\.

<a id="v0-39-0"></a>
## v0\.39\.0

<a id="release-summary-32"></a>
### Release Summary

Docs generation\:

- Improve boilerplate for ansible\.builtin documentation
- Render <code>choices</code> in return value documentation
- Add alternating background colors to option and return value tables

Also improves the Ansible release playbook/role\.

<a id="v0-38-2"></a>
## v0\.38\.2

<a id="release-summary-33"></a>
### Release Summary

Avoid creating role documentation for roles without argument spec\. Avoid naming collision with Ansible Sphinx config\'s <code>rst\_epilog</code> contents\.

<a id="v0-38-1"></a>
## v0\.38\.1

<a id="release-summary-34"></a>
### Release Summary

Fix for attributes support\: also allow new support value <code>N/A</code>\.

<a id="v0-38-0"></a>
## v0\.38\.0

<a id="release-summary-35"></a>
### Release Summary

Support CLI options for the ansible\.builtin\.ssh connection plugin\, and support ansible\-core 2\.12 module/plugin attributes\.

<a id="v0-37-0"></a>
## v0\.37\.0

<a id="v0-36-0"></a>
## v0\.36\.0

<a id="v0-35-0"></a>
## v0\.35\.0

<a id="v0-34-0"></a>
## v0\.34\.0

<a id="v0-33-0"></a>
## v0\.33\.0

<a id="v0-32-0"></a>
## v0\.32\.0

<a id="v0-31-0"></a>
## v0\.31\.0

<a id="v0-30-0"></a>
## v0\.30\.0

<a id="v0-29-0"></a>
## v0\.29\.0

<a id="v0-28-0"></a>
## v0\.28\.0

<a id="v0-27-0"></a>
## v0\.27\.0

<a id="v0-26-0"></a>
## v0\.26\.0

<a id="v0-25-0"></a>
## v0\.25\.0

<a id="v0-24-0"></a>
## v0\.24\.0

<a id="v0-23-0"></a>
## v0\.23\.0

<a id="v0-22-0"></a>
## v0\.22\.0

<a id="v0-21-0"></a>
## v0\.21\.0

<a id="v0-20-0"></a>
## v0\.20\.0

<a id="v0-19-0"></a>
## v0\.19\.0

<a id="v0-18-0"></a>
## v0\.18\.0

<a id="v0-17-0"></a>
## v0\.17\.0

<a id="v0-16-0"></a>
## v0\.16\.0

<a id="v0-15-0"></a>
## v0\.15\.0

<a id="v0-14-0"></a>
## v0\.14\.0

<a id="v0-13-0"></a>
## v0\.13\.0

<a id="v0-12-0"></a>
## v0\.12\.0

<a id="v0-11-0"></a>
## v0\.11\.0

<a id="v0-10-0"></a>
## v0\.10\.0

<a id="v0-9-0"></a>
## v0\.9\.0

<a id="v0-8-0"></a>
## v0\.8\.0

<a id="v0-7-0"></a>
## v0\.7\.0

<a id="v0-6-0"></a>
## v0\.6\.0

<a id="v0-5-0"></a>
## v0\.5\.0

<a id="v0-4-0"></a>
## v0\.4\.0

<a id="v0-3-0"></a>
## v0\.3\.0

<a id="v0-2-0"></a>
## v0\.2\.0

<a id="v0-1-0"></a>
## v0\.1\.0

<a id="release-summary-36"></a>
### Release Summary

Initial release\.
