Hello everyone,

We're happy to announce the release of the Ansible 7.0.0 package!

Ansible 7.0.0 depends on ansible-core 2.14.0 and includes a curated set of Ansible collections that provide a vast number of modules, plugins, and roles. This is the first stable release of Ansible 7.

How to get it
-------------

This release is available on PyPI and can be installed with pip:

```console
python3 -m pip install ansible==7.0.0 --user
```

The sources for this release can be found here:

Release tarball:

https://files.pythonhosted.org/packages/18/fd/963a3328d6f72e54d17dfbb40af6e9d6827333a5f1745c79c6d81b30dc85/ansible-7.0.0.tar.gz

SHA256:

73144e7e602715fab623005d2e71e503dddae86185e061fed861b2449c5618ea

Wheel package:

https://files.pythonhosted.org/packages/f7/62/4b3ee9140dd95b49ae43a0321e2a517fd6101797e620bbed7095a3ecd46e/ansible-7.0.0-py3-none-any.whl

SHA256:

2e9f519441780595ab173ac017210efc94c58633c9bc6e55917745d214cb4332


Some important details
----------------------

ansible-core is a separate package on which ansible depends. `pip install ansible` installs `ansible-core`, but it can also be installed independently of the ansible package.

Collections that have opted to join the Ansible 7 unified changelog will have an entry on this page:

https://github.com/ansible-community/ansible-build-data/blob/7.0.0/7/CHANGELOG-v7.md

For collections which have not opted-in to the unified changelog, you may find more information on

https://docs.ansible.com/ansible/latest/collections

or on the collection source repository. For example, the community.crypto collection is available at

https://docs.ansible.com/ansible/latest/collections/community/crypto/index.html

and you can find a link to the source repository under the “Repository (Sources)” button.

The changelog for ansible-core 2.14 installed by this release of Ansible 7 can be found here:

https://github.com/ansible/ansible/blob/v2.14.0/changelogs/CHANGELOG-v2.14.rst

What's the schedule for new Ansible releases after 7.0.0?
---------------------------------------------------------

The next release roadmap can be found at

https://docs.ansible.com/ansible/devel/roadmap/ansible_roadmap_index.html

The Ansible community package release schedule follows the Ansible Core release schedule, including, for example, delays for holidays. This means Ansible releases happen every four weeks through most of the year, but release dates may be delayed when Ansible Core releases are.

Subscribe to the Bullhorn for all future release dates, announcements, and Ansible contributor community news.

Visit this link to subscribe: https://bit.ly/subscribe-bullhorn

You can find all past Bullhorn issues on the Ansible Community Forum at:

https://forum.ansible.com/c/news/bullhorn/17

Join the new Ansible Community Forum to follow along and participate in all the project and release related discussions and announcements. Feel free to share your thoughts, feedback, ideas and concerns there.

Register here to join the Ansible Forum:

https://forum.ansible.com

Porting Help
------------

A unified porting guide for collections that have opted in is available here:

https://docs.ansible.com/ansible/devel/porting_guides/porting_guide_7.html

Getting collection updates from Ansible 7 with older releases of ansible-core
-----------------------------------------------------------------------------

Ansible 7 depends on ansible-core 2.14. Depending on your needs, you can get collection updates as they ship in the Ansible “batteries included” package while continuing to use older versions of ansible-core.

See the ansible-galaxy requirements file based on the collections from Ansible 7 for this use case:

https://github.com/ansible-community/ansible-build-data/blob/7.0.0/7/galaxy-requirements.yaml

After you download the requirements file, you can install the collections by running the following command:

```console
ansible-galaxy collection install -r galaxy-requirements.yaml
```

On behalf of the Ansible community, thank you and happy automating!

Cheers,
Ansible Release Management Working Group
