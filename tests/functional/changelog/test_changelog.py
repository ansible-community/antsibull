
from fixtures import collection_changelog, create_plugin


def test_changelog_init(collection_changelog, namespace='asfd'):
    collection_changelog.set_galaxy({
        'version': '1.0.0',
    })
    assert collection_changelog.run_tool('init', [collection_changelog.paths.base_dir]) == 0

    diff = collection_changelog.diff()
    assert diff.added_dirs == ['changelogs', 'changelogs/fragments']
    assert diff.added_files == ['changelogs/config.yaml']
    assert diff.removed_dirs == []
    assert diff.removed_files == []
    assert diff.changed_files == []

    config = diff.parse_yaml('changelogs/config.yaml')
    assert config['notesdir'] == 'fragments'
    assert config['changes_file'] == 'changelog.yaml'
    assert config['changelog_filename_template'] == 'CHANGELOG.rst'
    assert 'release_tag_re' not in config
    assert 'pre_release_tag_re' not in config
    assert config['title'] == collection_changelog.collection_name.title()


def test_changelog_release_empty(collection_changelog, namespace='asfd'):
    collection_changelog.set_galaxy({
        'version': '1.0.0',
    })
    collection_changelog.set_config(collection_changelog.config)
    collection_changelog.add_fragment_line('1.0.0.yml', 'release_summary', 'This is the first proper release.')
    collection_changelog.set_plugin_cache('1.0.0', {})

    assert collection_changelog.run_tool('release', ['--date', '2020-01-02']) == 0

    diff = collection_changelog.diff()
    assert diff.added_dirs == []
    assert diff.added_files == ['changelogs/CHANGELOG.rst', 'changelogs/changelog.yaml']
    assert diff.removed_dirs == []
    assert diff.removed_files == ['changelogs/fragments/1.0.0.yml']
    assert diff.changed_files == []

    changelog = diff.parse_yaml('changelogs/changelog.yaml')
    assert changelog['ancestor'] is None
    assert list(changelog['releases']) == ['1.0.0']
    assert changelog['releases']['1.0.0']['release_date'] == '2020-01-02'
    assert changelog['releases']['1.0.0']['changes'] == {'release_summary': 'This is the first proper release.'}
    assert changelog['releases']['1.0.0']['fragments'] == ['1.0.0.yml']
    assert 'modules' not in changelog['releases']['1.0.0']
    assert 'plugins' not in changelog['releases']['1.0.0']
    assert 'codename' not in changelog['releases']['1.0.0']


def test_changelog_release_plugin_cache(collection_changelog, namespace='asfd'):
    collection_changelog.set_galaxy({
        'version': '1.0.0',
    })
    collection_changelog.set_config(collection_changelog.config)
    collection_changelog.add_fragment_line('1.0.0.yml', 'release_summary', 'This is the first proper release.')
    collection_changelog.add_plugin('module', 'test_module.py', create_plugin(
        DOCUMENTATION={
            'name': 'test_module',
            'short_description': 'A test module',
            'version_added': '1.0.0',
            'description': ['This is a test module.'],
            'author': ['Someone'],
            'options': {},
        },
        EXAMPLES='',
        RETURN={},
    ))
    collection_changelog.add_plugin('module', 'old_module.py', create_plugin(
        DOCUMENTATION={
            'name': 'old_module',
            'short_description': 'An old module',
            'description': ['This is an old module.'],
            'author': ['Elder'],
            'options': {},
        },
        EXAMPLES='# Some examples\n',
        RETURN={},
    ), subdirs=['cloud', 'sky'])

    assert collection_changelog.run_tool('release', ['--date', '2020-01-02']) == 0

    diff = collection_changelog.diff()
    assert diff.added_dirs == []
    assert diff.added_files == ['changelogs/.plugin-cache.yaml', 'changelogs/CHANGELOG.rst', 'changelogs/changelog.yaml']
    assert diff.removed_dirs == []
    assert diff.removed_files == ['changelogs/fragments/1.0.0.yml']
    assert diff.changed_files == []

    plugin_cache = diff.parse_yaml('changelogs/.plugin-cache.yaml')
    assert plugin_cache['version'] == '1.0.0'

    # Plugin cache: modules
    assert sorted(plugin_cache['plugins']['module']) == ['old_module', 'test_module']
    assert plugin_cache['plugins']['module']['old_module']['name'] == 'old_module'
    assert plugin_cache['plugins']['module']['old_module']['namespace'] == 'cloud.sky'
    assert plugin_cache['plugins']['module']['old_module']['description'] == 'An old module'
    assert plugin_cache['plugins']['module']['old_module']['version_added'] is None
    assert plugin_cache['plugins']['module']['test_module']['name'] == 'test_module'
    assert plugin_cache['plugins']['module']['test_module']['namespace'] == ''
    assert plugin_cache['plugins']['module']['test_module']['description'] == 'A test module'
    assert plugin_cache['plugins']['module']['test_module']['version_added'] == '1.0.0'

    # Changelog
    changelog = diff.parse_yaml('changelogs/changelog.yaml')
    assert changelog['ancestor'] is None
    assert sorted(changelog['releases']) == ['1.0.0']
    assert changelog['releases']['1.0.0']['release_date'] == '2020-01-02'
    assert changelog['releases']['1.0.0']['changes'] == {'release_summary': 'This is the first proper release.'}
    assert changelog['releases']['1.0.0']['fragments'] == ['1.0.0.yml']
    assert len(changelog['releases']['1.0.0']['modules']) == 1
    assert changelog['releases']['1.0.0']['modules'][0]['name'] == 'test_module'
    assert changelog['releases']['1.0.0']['modules'][0]['namespace'] == ''
    assert changelog['releases']['1.0.0']['modules'][0]['description'] == 'A test module'
    assert 'version_added' not in changelog['releases']['1.0.0']['modules'][0]
