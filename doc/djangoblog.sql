/*
 Navicat Premium Dump SQL

 Source Server         : djangoblog
 Source Server Type    : MySQL
 Source Server Version : 80046 (8.0.46)
 Source Host           : localhost:3306
 Source Schema         : djangoblog

 Target Server Type    : MySQL
 Target Server Version : 80046 (8.0.46)
 File Encoding         : 65001

 Date: 07/10/2026 22:54:53
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for accounts_bloguser
-- ----------------------------
DROP TABLE IF EXISTS `accounts_bloguser`;
CREATE TABLE `accounts_bloguser`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) NULL DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `nickname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `source` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  `last_modify_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `username`(`username` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of accounts_bloguser
-- ----------------------------
INSERT INTO `accounts_bloguser` VALUES (1, 'pbkdf2_sha256$1000000$veEGZXDRXatD1nhMzIAlpp$CxeBS+4lZfSL9l1mka/ameLcoGxZ2z42tsOvYuMW1tE=', '2026-09-29 11:17:21.066179', 1, 'root', '', '', '2820522489@qq.com', 1, 1, '2026-09-12 17:16:06.984794', '', '', '2026-09-12 17:16:06.984796', '2026-09-12 17:16:06.984798');
INSERT INTO `accounts_bloguser` VALUES (2, 'pbkdf2_sha256$1000000$3Zmvm5ZpMWVCQwSacP920X$39DvdWYSlyr0ysZGqgwatEhqUy4z5c2Tu2RBdpyp2b0=', NULL, 0, '测试用户', '', '', 'test@test.com', 0, 1, '2026-09-12 17:59:02.319229', '', '', '2026-09-12 17:59:02.319233', '2026-09-12 17:59:02.319234');
INSERT INTO `accounts_bloguser` VALUES (3, 'pbkdf2_sha256$1000000$J1XFhUP3zYME7Uu3u7fdDA$GarnO26KlwO5SoPJwkSv507PlHjENYVSYMMqbcnEE1Y=', NULL, 0, 'zongshuai', '', '', '', 0, 1, '2026-09-13 19:11:30.738243', '', '', '2026-09-13 19:11:30.738246', '2026-09-13 19:11:30.738247');

-- ----------------------------
-- Table structure for accounts_bloguser_groups
-- ----------------------------
DROP TABLE IF EXISTS `accounts_bloguser_groups`;
CREATE TABLE `accounts_bloguser_groups`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `bloguser_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `accounts_bloguser_groups_bloguser_id_group_id_fc37e89b_uniq`(`bloguser_id` ASC, `group_id` ASC) USING BTREE,
  INDEX `accounts_bloguser_groups_group_id_98d76804_fk_auth_group_id`(`group_id` ASC) USING BTREE,
  CONSTRAINT `accounts_bloguser_gr_bloguser_id_a16ccbb7_fk_accounts_` FOREIGN KEY (`bloguser_id`) REFERENCES `accounts_bloguser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_bloguser_groups_group_id_98d76804_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of accounts_bloguser_groups
-- ----------------------------

-- ----------------------------
-- Table structure for accounts_bloguser_user_permissions
-- ----------------------------
DROP TABLE IF EXISTS `accounts_bloguser_user_permissions`;
CREATE TABLE `accounts_bloguser_user_permissions`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `bloguser_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `accounts_bloguser_user_p_bloguser_id_permission_i_14808777_uniq`(`bloguser_id` ASC, `permission_id` ASC) USING BTREE,
  INDEX `accounts_bloguser_us_permission_id_ae5159b9_fk_auth_perm`(`permission_id` ASC) USING BTREE,
  CONSTRAINT `accounts_bloguser_us_bloguser_id_7e1b5742_fk_accounts_` FOREIGN KEY (`bloguser_id`) REFERENCES `accounts_bloguser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_bloguser_us_permission_id_ae5159b9_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of accounts_bloguser_user_permissions
-- ----------------------------

-- ----------------------------
-- Table structure for auth_group
-- ----------------------------
DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE `auth_group`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_group
-- ----------------------------

-- ----------------------------
-- Table structure for auth_group_permissions
-- ----------------------------
DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE `auth_group_permissions`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `auth_group_permissions_group_id_permission_id_0cd325b0_uniq`(`group_id` ASC, `permission_id` ASC) USING BTREE,
  INDEX `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm`(`permission_id` ASC) USING BTREE,
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_group_permissions
-- ----------------------------

-- ----------------------------
-- Table structure for auth_permission
-- ----------------------------
DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE `auth_permission`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `auth_permission_content_type_id_codename_01ab375a_uniq`(`content_type_id` ASC, `codename` ASC) USING BTREE,
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 77 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_permission
-- ----------------------------
INSERT INTO `auth_permission` VALUES (1, 'Can add log entry', 1, 'add_logentry');
INSERT INTO `auth_permission` VALUES (2, 'Can change log entry', 1, 'change_logentry');
INSERT INTO `auth_permission` VALUES (3, 'Can delete log entry', 1, 'delete_logentry');
INSERT INTO `auth_permission` VALUES (4, 'Can view log entry', 1, 'view_logentry');
INSERT INTO `auth_permission` VALUES (5, 'Can add permission', 2, 'add_permission');
INSERT INTO `auth_permission` VALUES (6, 'Can change permission', 2, 'change_permission');
INSERT INTO `auth_permission` VALUES (7, 'Can delete permission', 2, 'delete_permission');
INSERT INTO `auth_permission` VALUES (8, 'Can view permission', 2, 'view_permission');
INSERT INTO `auth_permission` VALUES (9, 'Can add group', 3, 'add_group');
INSERT INTO `auth_permission` VALUES (10, 'Can change group', 3, 'change_group');
INSERT INTO `auth_permission` VALUES (11, 'Can delete group', 3, 'delete_group');
INSERT INTO `auth_permission` VALUES (12, 'Can view group', 3, 'view_group');
INSERT INTO `auth_permission` VALUES (13, 'Can add content type', 4, 'add_contenttype');
INSERT INTO `auth_permission` VALUES (14, 'Can change content type', 4, 'change_contenttype');
INSERT INTO `auth_permission` VALUES (15, 'Can delete content type', 4, 'delete_contenttype');
INSERT INTO `auth_permission` VALUES (16, 'Can view content type', 4, 'view_contenttype');
INSERT INTO `auth_permission` VALUES (17, 'Can add session', 5, 'add_session');
INSERT INTO `auth_permission` VALUES (18, 'Can change session', 5, 'change_session');
INSERT INTO `auth_permission` VALUES (19, 'Can delete session', 5, 'delete_session');
INSERT INTO `auth_permission` VALUES (20, 'Can view session', 5, 'view_session');
INSERT INTO `auth_permission` VALUES (21, 'Can add site', 6, 'add_site');
INSERT INTO `auth_permission` VALUES (22, 'Can change site', 6, 'change_site');
INSERT INTO `auth_permission` VALUES (23, 'Can delete site', 6, 'delete_site');
INSERT INTO `auth_permission` VALUES (24, 'Can view site', 6, 'view_site');
INSERT INTO `auth_permission` VALUES (25, 'Can add Website configuration', 7, 'add_blogsettings');
INSERT INTO `auth_permission` VALUES (26, 'Can change Website configuration', 7, 'change_blogsettings');
INSERT INTO `auth_permission` VALUES (27, 'Can delete Website configuration', 7, 'delete_blogsettings');
INSERT INTO `auth_permission` VALUES (28, 'Can view Website configuration', 7, 'view_blogsettings');
INSERT INTO `auth_permission` VALUES (29, 'Can add link', 8, 'add_links');
INSERT INTO `auth_permission` VALUES (30, 'Can change link', 8, 'change_links');
INSERT INTO `auth_permission` VALUES (31, 'Can delete link', 8, 'delete_links');
INSERT INTO `auth_permission` VALUES (32, 'Can view link', 8, 'view_links');
INSERT INTO `auth_permission` VALUES (33, 'Can add sidebar', 9, 'add_sidebar');
INSERT INTO `auth_permission` VALUES (34, 'Can change sidebar', 9, 'change_sidebar');
INSERT INTO `auth_permission` VALUES (35, 'Can delete sidebar', 9, 'delete_sidebar');
INSERT INTO `auth_permission` VALUES (36, 'Can view sidebar', 9, 'view_sidebar');
INSERT INTO `auth_permission` VALUES (37, 'Can add tag', 10, 'add_tag');
INSERT INTO `auth_permission` VALUES (38, 'Can change tag', 10, 'change_tag');
INSERT INTO `auth_permission` VALUES (39, 'Can delete tag', 10, 'delete_tag');
INSERT INTO `auth_permission` VALUES (40, 'Can view tag', 10, 'view_tag');
INSERT INTO `auth_permission` VALUES (41, 'Can add category', 11, 'add_category');
INSERT INTO `auth_permission` VALUES (42, 'Can change category', 11, 'change_category');
INSERT INTO `auth_permission` VALUES (43, 'Can delete category', 11, 'delete_category');
INSERT INTO `auth_permission` VALUES (44, 'Can view category', 11, 'view_category');
INSERT INTO `auth_permission` VALUES (45, 'Can add article', 12, 'add_article');
INSERT INTO `auth_permission` VALUES (46, 'Can change article', 12, 'change_article');
INSERT INTO `auth_permission` VALUES (47, 'Can delete article', 12, 'delete_article');
INSERT INTO `auth_permission` VALUES (48, 'Can view article', 12, 'view_article');
INSERT INTO `auth_permission` VALUES (49, 'Can add user', 13, 'add_bloguser');
INSERT INTO `auth_permission` VALUES (50, 'Can change user', 13, 'change_bloguser');
INSERT INTO `auth_permission` VALUES (51, 'Can delete user', 13, 'delete_bloguser');
INSERT INTO `auth_permission` VALUES (52, 'Can view user', 13, 'view_bloguser');
INSERT INTO `auth_permission` VALUES (53, 'Can add comment', 14, 'add_comment');
INSERT INTO `auth_permission` VALUES (54, 'Can change comment', 14, 'change_comment');
INSERT INTO `auth_permission` VALUES (55, 'Can delete comment', 14, 'delete_comment');
INSERT INTO `auth_permission` VALUES (56, 'Can view comment', 14, 'view_comment');
INSERT INTO `auth_permission` VALUES (57, 'Can add comment reaction', 15, 'add_commentreaction');
INSERT INTO `auth_permission` VALUES (58, 'Can change comment reaction', 15, 'change_commentreaction');
INSERT INTO `auth_permission` VALUES (59, 'Can delete comment reaction', 15, 'delete_commentreaction');
INSERT INTO `auth_permission` VALUES (60, 'Can view comment reaction', 15, 'view_commentreaction');
INSERT INTO `auth_permission` VALUES (61, 'Can add oauth配置', 16, 'add_oauthconfig');
INSERT INTO `auth_permission` VALUES (62, 'Can change oauth配置', 16, 'change_oauthconfig');
INSERT INTO `auth_permission` VALUES (63, 'Can delete oauth配置', 16, 'delete_oauthconfig');
INSERT INTO `auth_permission` VALUES (64, 'Can view oauth配置', 16, 'view_oauthconfig');
INSERT INTO `auth_permission` VALUES (65, 'Can add oauth user', 17, 'add_oauthuser');
INSERT INTO `auth_permission` VALUES (66, 'Can change oauth user', 17, 'change_oauthuser');
INSERT INTO `auth_permission` VALUES (67, 'Can delete oauth user', 17, 'delete_oauthuser');
INSERT INTO `auth_permission` VALUES (68, 'Can view oauth user', 17, 'view_oauthuser');
INSERT INTO `auth_permission` VALUES (69, 'Can add 命令', 18, 'add_commands');
INSERT INTO `auth_permission` VALUES (70, 'Can change 命令', 18, 'change_commands');
INSERT INTO `auth_permission` VALUES (71, 'Can delete 命令', 18, 'delete_commands');
INSERT INTO `auth_permission` VALUES (72, 'Can view 命令', 18, 'view_commands');
INSERT INTO `auth_permission` VALUES (73, 'Can add 邮件发送log', 19, 'add_emailsendlog');
INSERT INTO `auth_permission` VALUES (74, 'Can change 邮件发送log', 19, 'change_emailsendlog');
INSERT INTO `auth_permission` VALUES (75, 'Can delete 邮件发送log', 19, 'delete_emailsendlog');
INSERT INTO `auth_permission` VALUES (76, 'Can view 邮件发送log', 19, 'view_emailsendlog');

-- ----------------------------
-- Table structure for blog_article
-- ----------------------------
DROP TABLE IF EXISTS `blog_article`;
CREATE TABLE `blog_article`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `body` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `pub_time` datetime(6) NOT NULL,
  `status` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `comment_status` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `type` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `views` int UNSIGNED NOT NULL,
  `article_order` int NOT NULL,
  `show_toc` tinyint(1) NOT NULL,
  `author_id` bigint NOT NULL,
  `category_id` int NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  `last_modify_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `title`(`title` ASC) USING BTREE,
  INDEX `idx_type_status_pub`(`type` ASC, `status` ASC, `pub_time` DESC) USING BTREE,
  INDEX `idx_status_views`(`status` ASC, `views` DESC) USING BTREE,
  INDEX `idx_author_status_type`(`author_id` ASC, `status` ASC, `type` ASC) USING BTREE,
  INDEX `idx_category_status`(`category_id` ASC, `status` ASC) USING BTREE,
  CONSTRAINT `blog_article_author_id_905add38_fk_accounts_bloguser_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_bloguser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `blog_article_category_id_7e38f15e_fk_blog_category_id` FOREIGN KEY (`category_id`) REFERENCES `blog_category` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `blog_article_chk_1` CHECK (`views` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 21 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of blog_article
-- ----------------------------
INSERT INTO `blog_article` VALUES (1, 'nice title 1', 'nice content 1', '2026-09-12 17:59:05.440883', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:05.440875', '2026-09-12 17:59:05.440879');
INSERT INTO `blog_article` VALUES (2, 'nice title 2', 'nice content 2', '2026-09-12 17:59:06.902357', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:06.902350', '2026-09-12 17:59:06.902353');
INSERT INTO `blog_article` VALUES (3, 'nice title 3', 'nice content 3', '2026-09-12 17:59:07.481960', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:07.481954', '2026-09-12 17:59:07.481958');
INSERT INTO `blog_article` VALUES (4, 'nice title 4', 'nice content 4', '2026-09-12 17:59:08.354364', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:08.354357', '2026-09-12 17:59:08.354361');
INSERT INTO `blog_article` VALUES (5, 'nice title 5', 'nice content 5', '2026-09-12 17:59:09.205390', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:09.205383', '2026-09-12 17:59:09.205387');
INSERT INTO `blog_article` VALUES (6, 'nice title 6', 'nice content 6', '2026-09-12 17:59:10.191753', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:10.191747', '2026-09-12 17:59:10.191750');
INSERT INTO `blog_article` VALUES (7, 'nice title 7', 'nice content 7', '2026-09-12 17:59:10.940679', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:10.940673', '2026-09-12 17:59:10.940677');
INSERT INTO `blog_article` VALUES (8, 'nice title 8', 'nice content 8', '2026-09-12 17:59:11.506671', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:11.506666', '2026-09-12 17:59:11.506668');
INSERT INTO `blog_article` VALUES (9, 'nice title 9', 'nice content 9', '2026-09-12 17:59:12.366370', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:12.366364', '2026-09-12 17:59:12.366366');
INSERT INTO `blog_article` VALUES (10, 'nice title 10', 'nice content 10', '2026-09-12 17:59:12.960272', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:12.960266', '2026-09-12 17:59:12.960269');
INSERT INTO `blog_article` VALUES (11, 'nice title 11', 'nice content 11', '2026-09-12 17:59:13.826162', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:13.826155', '2026-09-12 17:59:13.826158');
INSERT INTO `blog_article` VALUES (12, 'nice title 12', 'nice content 12', '2026-09-12 17:59:14.369063', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:14.369056', '2026-09-12 17:59:14.369060');
INSERT INTO `blog_article` VALUES (13, 'nice title 13', 'nice content 13', '2026-09-12 17:59:15.150938', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:15.150931', '2026-09-12 17:59:15.150935');
INSERT INTO `blog_article` VALUES (14, 'nice title 14', 'nice content 14', '2026-09-12 17:59:15.700988', 'p', 'o', 'a', 0, 0, 0, 2, 2, '2026-09-12 17:59:15.700981', '2026-09-12 17:59:15.700985');
INSERT INTO `blog_article` VALUES (15, 'nice title 15', 'nice content 15', '2026-09-12 17:59:16.377865', 'p', 'o', 'a', 1, 0, 0, 2, 2, '2026-09-12 17:59:16.377858', '2026-09-12 17:59:16.377862');
INSERT INTO `blog_article` VALUES (16, 'nice title 16', 'nice content 16', '2026-09-12 17:59:16.971893', 'p', 'o', 'a', 2, 0, 0, 2, 2, '2026-09-12 17:59:16.971887', '2026-09-12 17:59:16.971890');
INSERT INTO `blog_article` VALUES (17, 'nice title 17', 'nice content 17', '2026-09-12 17:59:17.600848', 'p', 'o', 'a', 2, 0, 0, 2, 2, '2026-09-12 17:59:17.600841', '2026-09-12 17:59:17.600844');
INSERT INTO `blog_article` VALUES (18, 'nice title 18', 'nice content 18', '2026-09-12 17:59:18.565093', 'p', 'o', 'a', 5, 0, 0, 2, 2, '2026-09-12 17:59:18.565087', '2026-09-12 17:59:18.565091');
INSERT INTO `blog_article` VALUES (19, 'nice title 19', 'nice content 19', '2026-09-12 17:59:19.311705', 'p', 'o', 'a', 5, 0, 0, 2, 2, '2026-09-12 17:59:19.311698', '2026-09-12 17:59:19.311702');
INSERT INTO `blog_article` VALUES (20, '老子天下第一', '闹擦了哈喽哈喽才能拉胯你擦吗，参比制剂看过才u好费劲啊好吧', '2026-09-29 11:28:00.000000', 'p', 'o', 'a', 1, 0, 0, 1, 1, '2026-09-29 11:30:47.313070', '2026-09-29 11:30:47.313073');

-- ----------------------------
-- Table structure for blog_article_tags
-- ----------------------------
DROP TABLE IF EXISTS `blog_article_tags`;
CREATE TABLE `blog_article_tags`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `article_id` int NOT NULL,
  `tag_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `blog_article_tags_article_id_tag_id_b78a22e9_uniq`(`article_id` ASC, `tag_id` ASC) USING BTREE,
  INDEX `blog_article_tags_tag_id_88eb3ed9_fk_blog_tag_id`(`tag_id` ASC) USING BTREE,
  CONSTRAINT `blog_article_tags_article_id_82c02dd6_fk_blog_article_id` FOREIGN KEY (`article_id`) REFERENCES `blog_article` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `blog_article_tags_tag_id_88eb3ed9_fk_blog_tag_id` FOREIGN KEY (`tag_id`) REFERENCES `blog_tag` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 39 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of blog_article_tags
-- ----------------------------
INSERT INTO `blog_article_tags` VALUES (2, 1, 1);
INSERT INTO `blog_article_tags` VALUES (1, 1, 2);
INSERT INTO `blog_article_tags` VALUES (4, 2, 1);
INSERT INTO `blog_article_tags` VALUES (3, 2, 3);
INSERT INTO `blog_article_tags` VALUES (6, 3, 1);
INSERT INTO `blog_article_tags` VALUES (5, 3, 4);
INSERT INTO `blog_article_tags` VALUES (8, 4, 1);
INSERT INTO `blog_article_tags` VALUES (7, 4, 5);
INSERT INTO `blog_article_tags` VALUES (10, 5, 1);
INSERT INTO `blog_article_tags` VALUES (9, 5, 6);
INSERT INTO `blog_article_tags` VALUES (12, 6, 1);
INSERT INTO `blog_article_tags` VALUES (11, 6, 7);
INSERT INTO `blog_article_tags` VALUES (14, 7, 1);
INSERT INTO `blog_article_tags` VALUES (13, 7, 8);
INSERT INTO `blog_article_tags` VALUES (16, 8, 1);
INSERT INTO `blog_article_tags` VALUES (15, 8, 9);
INSERT INTO `blog_article_tags` VALUES (18, 9, 1);
INSERT INTO `blog_article_tags` VALUES (17, 9, 10);
INSERT INTO `blog_article_tags` VALUES (20, 10, 1);
INSERT INTO `blog_article_tags` VALUES (19, 10, 11);
INSERT INTO `blog_article_tags` VALUES (22, 11, 1);
INSERT INTO `blog_article_tags` VALUES (21, 11, 12);
INSERT INTO `blog_article_tags` VALUES (24, 12, 1);
INSERT INTO `blog_article_tags` VALUES (23, 12, 13);
INSERT INTO `blog_article_tags` VALUES (26, 13, 1);
INSERT INTO `blog_article_tags` VALUES (25, 13, 14);
INSERT INTO `blog_article_tags` VALUES (28, 14, 1);
INSERT INTO `blog_article_tags` VALUES (27, 14, 15);
INSERT INTO `blog_article_tags` VALUES (30, 15, 1);
INSERT INTO `blog_article_tags` VALUES (29, 15, 16);
INSERT INTO `blog_article_tags` VALUES (32, 16, 1);
INSERT INTO `blog_article_tags` VALUES (31, 16, 17);
INSERT INTO `blog_article_tags` VALUES (34, 17, 1);
INSERT INTO `blog_article_tags` VALUES (33, 17, 18);
INSERT INTO `blog_article_tags` VALUES (36, 18, 1);
INSERT INTO `blog_article_tags` VALUES (35, 18, 19);
INSERT INTO `blog_article_tags` VALUES (38, 19, 1);
INSERT INTO `blog_article_tags` VALUES (37, 19, 20);

-- ----------------------------
-- Table structure for blog_blogsettings
-- ----------------------------
DROP TABLE IF EXISTS `blog_blogsettings`;
CREATE TABLE `blog_blogsettings`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `site_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `site_description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `site_seo_description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `site_keywords` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `article_sub_length` int NOT NULL,
  `sidebar_article_count` int NOT NULL,
  `sidebar_comment_count` int NOT NULL,
  `article_comment_count` int NOT NULL,
  `show_google_adsense` tinyint(1) NOT NULL,
  `google_adsense_codes` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `open_site_comment` tinyint(1) NOT NULL,
  `beian_code` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `analytics_code` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `show_gongan_code` tinyint(1) NOT NULL,
  `gongan_beiancode` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `global_footer` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `global_header` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `comment_need_review` tinyint(1) NOT NULL,
  `color_scheme` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of blog_blogsettings
-- ----------------------------
INSERT INTO `blog_blogsettings` VALUES (1, 'djangoblog', '基于Django的博客系统', '基于Django的博客系统', 'Django,Python', 300, 10, 5, 5, 0, '', 1, '', '', 0, '', '', '', 0, 'purple');

-- ----------------------------
-- Table structure for blog_category
-- ----------------------------
DROP TABLE IF EXISTS `blog_category`;
CREATE TABLE `blog_category`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `slug` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `index` int NOT NULL,
  `parent_category_id` int NULL DEFAULT NULL,
  `creation_time` datetime(6) NOT NULL,
  `last_modify_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  INDEX `blog_category_parent_category_id_f50c3c0c_fk_blog_category_id`(`parent_category_id` ASC) USING BTREE,
  INDEX `blog_category_slug_92643dc5`(`slug` ASC) USING BTREE,
  CONSTRAINT `blog_category_parent_category_id_f50c3c0c_fk_blog_category_id` FOREIGN KEY (`parent_category_id`) REFERENCES `blog_category` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of blog_category
-- ----------------------------
INSERT INTO `blog_category` VALUES (1, '我是父类目', 'wo-shi-fu-lei-mu', 0, NULL, '2026-09-12 17:59:02.682033', '2026-09-12 17:59:02.682038');
INSERT INTO `blog_category` VALUES (2, '子类目', 'zi-lei-mu', 0, 1, '2026-09-12 17:59:02.837223', '2026-09-12 17:59:02.837227');

-- ----------------------------
-- Table structure for blog_links
-- ----------------------------
DROP TABLE IF EXISTS `blog_links`;
CREATE TABLE `blog_links`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `link` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `sequence` int NOT NULL,
  `is_enable` tinyint(1) NOT NULL,
  `show_type` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_mod_time` datetime(6) NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  UNIQUE INDEX `sequence`(`sequence` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of blog_links
-- ----------------------------

-- ----------------------------
-- Table structure for blog_sidebar
-- ----------------------------
DROP TABLE IF EXISTS `blog_sidebar`;
CREATE TABLE `blog_sidebar`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `sequence` int NOT NULL,
  `is_enable` tinyint(1) NOT NULL,
  `last_mod_time` datetime(6) NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `sequence`(`sequence` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of blog_sidebar
-- ----------------------------

-- ----------------------------
-- Table structure for blog_tag
-- ----------------------------
DROP TABLE IF EXISTS `blog_tag`;
CREATE TABLE `blog_tag`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `slug` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  `last_modify_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  INDEX `blog_tag_slug_01068d0e`(`slug` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 21 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of blog_tag
-- ----------------------------
INSERT INTO `blog_tag` VALUES (1, '标签', 'biao-qian', '2026-09-12 17:59:04.275980', '2026-09-12 17:59:04.275984');
INSERT INTO `blog_tag` VALUES (2, '标签1', 'biao-qian-1', '2026-09-12 17:59:06.334227', '2026-09-12 17:59:06.334230');
INSERT INTO `blog_tag` VALUES (3, '标签2', 'biao-qian-2', '2026-09-12 17:59:07.115974', '2026-09-12 17:59:07.115978');
INSERT INTO `blog_tag` VALUES (4, '标签3', 'biao-qian-3', '2026-09-12 17:59:07.689402', '2026-09-12 17:59:07.689405');
INSERT INTO `blog_tag` VALUES (5, '标签4', 'biao-qian-4', '2026-09-12 17:59:08.571209', '2026-09-12 17:59:08.571212');
INSERT INTO `blog_tag` VALUES (6, '标签5', 'biao-qian-5', '2026-09-12 17:59:09.575010', '2026-09-12 17:59:09.575013');
INSERT INTO `blog_tag` VALUES (7, '标签6', 'biao-qian-6', '2026-09-12 17:59:10.440985', '2026-09-12 17:59:10.440988');
INSERT INTO `blog_tag` VALUES (8, '标签7', 'biao-qian-7', '2026-09-12 17:59:11.142674', '2026-09-12 17:59:11.142677');
INSERT INTO `blog_tag` VALUES (9, '标签8', 'biao-qian-8', '2026-09-12 17:59:11.713995', '2026-09-12 17:59:11.713998');
INSERT INTO `blog_tag` VALUES (10, '标签9', 'biao-qian-9', '2026-09-12 17:59:12.593184', '2026-09-12 17:59:12.593187');
INSERT INTO `blog_tag` VALUES (11, '标签10', 'biao-qian-10', '2026-09-12 17:59:13.291935', '2026-09-12 17:59:13.291938');
INSERT INTO `blog_tag` VALUES (12, '标签11', 'biao-qian-11', '2026-09-12 17:59:14.073220', '2026-09-12 17:59:14.073225');
INSERT INTO `blog_tag` VALUES (13, '标签12', 'biao-qian-12', '2026-09-12 17:59:14.596923', '2026-09-12 17:59:14.596926');
INSERT INTO `blog_tag` VALUES (14, '标签13', 'biao-qian-13', '2026-09-12 17:59:15.380234', '2026-09-12 17:59:15.380238');
INSERT INTO `blog_tag` VALUES (15, '标签14', 'biao-qian-14', '2026-09-12 17:59:15.906392', '2026-09-12 17:59:15.906395');
INSERT INTO `blog_tag` VALUES (16, '标签15', 'biao-qian-15', '2026-09-12 17:59:16.597381', '2026-09-12 17:59:16.597384');
INSERT INTO `blog_tag` VALUES (17, '标签16', 'biao-qian-16', '2026-09-12 17:59:17.295387', '2026-09-12 17:59:17.295390');
INSERT INTO `blog_tag` VALUES (18, '标签17', 'biao-qian-17', '2026-09-12 17:59:17.903202', '2026-09-12 17:59:17.903205');
INSERT INTO `blog_tag` VALUES (19, '标签18', 'biao-qian-18', '2026-09-12 17:59:18.896171', '2026-09-12 17:59:18.896174');
INSERT INTO `blog_tag` VALUES (20, '标签19', 'biao-qian-19', '2026-09-12 17:59:19.669358', '2026-09-12 17:59:19.669361');

-- ----------------------------
-- Table structure for comments_comment
-- ----------------------------
DROP TABLE IF EXISTS `comments_comment`;
CREATE TABLE `comments_comment`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `body` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_enable` tinyint(1) NOT NULL,
  `article_id` int NOT NULL,
  `author_id` bigint NOT NULL,
  `parent_comment_id` bigint NULL DEFAULT NULL,
  `creation_time` datetime(6) NOT NULL,
  `last_modify_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `comments_comment_author_id_334ce9e2_fk_accounts_bloguser_id`(`author_id` ASC) USING BTREE,
  INDEX `comments_comment_parent_comment_id_71289d4a_fk_comments_`(`parent_comment_id` ASC) USING BTREE,
  INDEX `idx_art_parent_enable`(`article_id` ASC, `parent_comment_id` ASC, `is_enable` ASC) USING BTREE,
  INDEX `idx_enable_id`(`is_enable` ASC, `id` DESC) USING BTREE,
  CONSTRAINT `comments_comment_article_id_94fe60a2_fk_blog_article_id` FOREIGN KEY (`article_id`) REFERENCES `blog_article` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `comments_comment_author_id_334ce9e2_fk_accounts_bloguser_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_bloguser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `comments_comment_parent_comment_id_71289d4a_fk_comments_` FOREIGN KEY (`parent_comment_id`) REFERENCES `comments_comment` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of comments_comment
-- ----------------------------

-- ----------------------------
-- Table structure for comments_commentreaction
-- ----------------------------
DROP TABLE IF EXISTS `comments_commentreaction`;
CREATE TABLE `comments_commentreaction`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `reaction_type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `comment_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `comments_commentreaction_comment_id_user_id_react_59e7fb94_uniq`(`comment_id` ASC, `user_id` ASC, `reaction_type` ASC) USING BTREE,
  INDEX `comments_commentreac_user_id_1be332d5_fk_accounts_`(`user_id` ASC) USING BTREE,
  INDEX `idx_comment_reaction`(`comment_id` ASC, `reaction_type` ASC) USING BTREE,
  CONSTRAINT `comments_commentreac_comment_id_873aaba8_fk_comments_` FOREIGN KEY (`comment_id`) REFERENCES `comments_comment` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `comments_commentreac_user_id_1be332d5_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_bloguser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of comments_commentreaction
-- ----------------------------

-- ----------------------------
-- Table structure for django_admin_log
-- ----------------------------
DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE `django_admin_log`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `object_repr` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint UNSIGNED NOT NULL,
  `change_message` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NULL DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `django_admin_log_content_type_id_c4bce8eb_fk_django_co`(`content_type_id` ASC) USING BTREE,
  INDEX `django_admin_log_user_id_c564eba6_fk_accounts_bloguser_id`(`user_id` ASC) USING BTREE,
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_bloguser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_bloguser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `django_admin_log_chk_1` CHECK (`action_flag` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_admin_log
-- ----------------------------
INSERT INTO `django_admin_log` VALUES (1, '2026-09-13 19:11:31.563191', '3', '', 1, '[{\"added\": {}}]', 13, 1);
INSERT INTO `django_admin_log` VALUES (2, '2026-09-29 11:30:51.183625', '20', '老子天下第一', 1, '[{\"added\": {}}]', 12, 1);

-- ----------------------------
-- Table structure for django_content_type
-- ----------------------------
DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE `django_content_type`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `django_content_type_app_label_model_76bd3d3b_uniq`(`app_label` ASC, `model` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 20 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_content_type
-- ----------------------------
INSERT INTO `django_content_type` VALUES (13, 'accounts', 'bloguser');
INSERT INTO `django_content_type` VALUES (1, 'admin', 'logentry');
INSERT INTO `django_content_type` VALUES (3, 'auth', 'group');
INSERT INTO `django_content_type` VALUES (2, 'auth', 'permission');
INSERT INTO `django_content_type` VALUES (12, 'blog', 'article');
INSERT INTO `django_content_type` VALUES (7, 'blog', 'blogsettings');
INSERT INTO `django_content_type` VALUES (11, 'blog', 'category');
INSERT INTO `django_content_type` VALUES (8, 'blog', 'links');
INSERT INTO `django_content_type` VALUES (9, 'blog', 'sidebar');
INSERT INTO `django_content_type` VALUES (10, 'blog', 'tag');
INSERT INTO `django_content_type` VALUES (14, 'comments', 'comment');
INSERT INTO `django_content_type` VALUES (15, 'comments', 'commentreaction');
INSERT INTO `django_content_type` VALUES (4, 'contenttypes', 'contenttype');
INSERT INTO `django_content_type` VALUES (16, 'oauth', 'oauthconfig');
INSERT INTO `django_content_type` VALUES (17, 'oauth', 'oauthuser');
INSERT INTO `django_content_type` VALUES (18, 'servermanager', 'commands');
INSERT INTO `django_content_type` VALUES (19, 'servermanager', 'emailsendlog');
INSERT INTO `django_content_type` VALUES (5, 'sessions', 'session');
INSERT INTO `django_content_type` VALUES (6, 'sites', 'site');

-- ----------------------------
-- Table structure for django_migrations
-- ----------------------------
DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE `django_migrations`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 41 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_migrations
-- ----------------------------
INSERT INTO `django_migrations` VALUES (1, 'contenttypes', '0001_initial', '2026-09-12 17:14:41.975437');
INSERT INTO `django_migrations` VALUES (2, 'contenttypes', '0002_remove_content_type_name', '2026-09-12 17:14:42.154935');
INSERT INTO `django_migrations` VALUES (3, 'auth', '0001_initial', '2026-09-12 17:14:42.645982');
INSERT INTO `django_migrations` VALUES (4, 'auth', '0002_alter_permission_name_max_length', '2026-09-12 17:14:42.750438');
INSERT INTO `django_migrations` VALUES (5, 'auth', '0003_alter_user_email_max_length', '2026-09-12 17:14:42.759425');
INSERT INTO `django_migrations` VALUES (6, 'auth', '0004_alter_user_username_opts', '2026-09-12 17:14:42.767579');
INSERT INTO `django_migrations` VALUES (7, 'auth', '0005_alter_user_last_login_null', '2026-09-12 17:14:42.777410');
INSERT INTO `django_migrations` VALUES (8, 'auth', '0006_require_contenttypes_0002', '2026-09-12 17:14:42.783619');
INSERT INTO `django_migrations` VALUES (9, 'auth', '0007_alter_validators_add_error_messages', '2026-09-12 17:14:42.793242');
INSERT INTO `django_migrations` VALUES (10, 'auth', '0008_alter_user_username_max_length', '2026-09-12 17:14:42.802190');
INSERT INTO `django_migrations` VALUES (11, 'auth', '0009_alter_user_last_name_max_length', '2026-09-12 17:14:42.811333');
INSERT INTO `django_migrations` VALUES (12, 'auth', '0010_alter_group_name_max_length', '2026-09-12 17:14:42.832522');
INSERT INTO `django_migrations` VALUES (13, 'auth', '0011_update_proxy_permissions', '2026-09-12 17:14:42.841587');
INSERT INTO `django_migrations` VALUES (14, 'auth', '0012_alter_user_first_name_max_length', '2026-09-12 17:14:42.850209');
INSERT INTO `django_migrations` VALUES (15, 'accounts', '0001_initial', '2026-09-12 17:14:43.418869');
INSERT INTO `django_migrations` VALUES (16, 'accounts', '0002_alter_bloguser_options_remove_bloguser_created_time_and_more', '2026-09-12 17:14:43.800511');
INSERT INTO `django_migrations` VALUES (17, 'admin', '0001_initial', '2026-09-12 17:14:44.047357');
INSERT INTO `django_migrations` VALUES (18, 'admin', '0002_logentry_remove_auto_add', '2026-09-12 17:14:44.059187');
INSERT INTO `django_migrations` VALUES (19, 'admin', '0003_logentry_add_action_flag_choices', '2026-09-12 17:14:44.070198');
INSERT INTO `django_migrations` VALUES (20, 'blog', '0001_initial', '2026-09-12 17:14:45.011886');
INSERT INTO `django_migrations` VALUES (21, 'blog', '0002_blogsettings_global_footer_and_more', '2026-09-12 17:14:45.147359');
INSERT INTO `django_migrations` VALUES (22, 'blog', '0003_blogsettings_comment_need_review', '2026-09-12 17:14:45.230991');
INSERT INTO `django_migrations` VALUES (23, 'blog', '0004_rename_analyticscode_blogsettings_analytics_code_and_more', '2026-09-12 17:14:45.323531');
INSERT INTO `django_migrations` VALUES (24, 'blog', '0005_alter_article_options_alter_category_options_and_more', '2026-09-12 17:14:46.957289');
INSERT INTO `django_migrations` VALUES (25, 'blog', '0006_alter_blogsettings_options', '2026-09-12 17:14:46.965334');
INSERT INTO `django_migrations` VALUES (26, 'blog', '0007_article_idx_type_status_pub_article_idx_status_views_and_more', '2026-09-12 17:14:47.144930');
INSERT INTO `django_migrations` VALUES (27, 'blog', '0008_blogsettings_color_scheme', '2026-09-12 17:14:47.227762');
INSERT INTO `django_migrations` VALUES (28, 'comments', '0001_initial', '2026-09-12 17:14:47.579152');
INSERT INTO `django_migrations` VALUES (29, 'comments', '0002_alter_comment_is_enable', '2026-09-12 17:14:47.595204');
INSERT INTO `django_migrations` VALUES (30, 'comments', '0003_alter_comment_options_remove_comment_created_time_and_more', '2026-09-12 17:14:48.071494');
INSERT INTO `django_migrations` VALUES (31, 'comments', '0004_comment_idx_art_parent_enable_comment_idx_enable_id', '2026-09-12 17:14:48.156592');
INSERT INTO `django_migrations` VALUES (32, 'comments', '0005_commentreaction', '2026-09-12 17:14:48.464139');
INSERT INTO `django_migrations` VALUES (33, 'oauth', '0001_initial', '2026-09-12 17:14:48.909842');
INSERT INTO `django_migrations` VALUES (34, 'oauth', '0002_alter_oauthconfig_options_alter_oauthuser_options_and_more', '2026-09-12 17:14:49.569831');
INSERT INTO `django_migrations` VALUES (35, 'oauth', '0003_alter_oauthuser_nickname', '2026-09-12 17:14:49.585114');
INSERT INTO `django_migrations` VALUES (36, 'servermanager', '0001_initial', '2026-09-12 17:14:49.664634');
INSERT INTO `django_migrations` VALUES (37, 'servermanager', '0002_alter_emailsendlog_options_and_more', '2026-09-12 17:14:49.752279');
INSERT INTO `django_migrations` VALUES (38, 'sessions', '0001_initial', '2026-09-12 17:14:49.818065');
INSERT INTO `django_migrations` VALUES (39, 'sites', '0001_initial', '2026-09-12 17:14:49.856611');
INSERT INTO `django_migrations` VALUES (40, 'sites', '0002_alter_domain_unique', '2026-09-12 17:14:49.885054');

-- ----------------------------
-- Table structure for django_session
-- ----------------------------
DROP TABLE IF EXISTS `django_session`;
CREATE TABLE `django_session`  (
  `session_key` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`) USING BTREE,
  INDEX `django_session_expire_date_a5c62663`(`expire_date` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_session
-- ----------------------------
INSERT INTO `django_session` VALUES ('5xrjwfpp4r6f1svly16purxkrk9sttjt', '.eJxVjMsKwjAQAP9lz1KSpnn1KPQonjyHzWZri20KTXsS_10UBb3OMHOHgPs2hL3wGsYELUg4_LKIdOP8Eki07Hkr1ZtPy3XMX1t1M47Teb0UXjPOfFoST8dP-bcbsAzQgjDCNVHZHp1jUYtGaeXJ1g1Gx0mi11YlaWS0wlpt2GNPtUmKjPaUYoTHE62SPXA:1xBOLJ:vHL0KDsViXGYtjdcqjKeqrxv8SCWj6m9J8ApO16h4ec', '2026-10-13 11:17:21.447167');
INSERT INTO `django_session` VALUES ('fwp060fw98nn87s5of9zyd3ttigu48lj', '.eJxVjEsKwjAUAO-StUg-za9LwaW4cl1eklcbbBNJWlDEu0tFQbczzDxIB8s8dEvF0sVAWsLI5pc58BdMqwDv85Lmun3zMZ9j-trtfoI4HsupYkkw4SEHHHef8m83QB1IS6iipnFC92AMUk4bIYX1mjfgDAYGVmoRmGJOU62lQgu95yoIr6T1wbl1WrHWmFOHt2ssd9IyTq2i9PkCY1FF3w:1x5KfL:hb828_C51kO6o0BB-LVbYXYeZ1la7JWdNzVtYtXvCXs', '2026-09-26 18:08:59.277264');

-- ----------------------------
-- Table structure for django_site
-- ----------------------------
DROP TABLE IF EXISTS `django_site`;
CREATE TABLE `django_site`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `domain` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `django_site_domain_a2e37b91_uniq`(`domain` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_site
-- ----------------------------
INSERT INTO `django_site` VALUES (1, 'example.com', 'example.com');

-- ----------------------------
-- Table structure for oauth_oauthconfig
-- ----------------------------
DROP TABLE IF EXISTS `oauth_oauthconfig`;
CREATE TABLE `oauth_oauthconfig`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `appkey` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `appsecret` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `callback_url` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_enable` tinyint(1) NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  `last_modify_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of oauth_oauthconfig
-- ----------------------------

-- ----------------------------
-- Table structure for oauth_oauthuser
-- ----------------------------
DROP TABLE IF EXISTS `oauth_oauthuser`;
CREATE TABLE `oauth_oauthuser`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `openid` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `nickname` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `token` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `picture` varchar(350) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `author_id` bigint NULL DEFAULT NULL,
  `creation_time` datetime(6) NOT NULL,
  `last_modify_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `oauth_oauthuser_author_id_a975bef0_fk_accounts_bloguser_id`(`author_id` ASC) USING BTREE,
  CONSTRAINT `oauth_oauthuser_author_id_a975bef0_fk_accounts_bloguser_id` FOREIGN KEY (`author_id`) REFERENCES `accounts_bloguser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of oauth_oauthuser
-- ----------------------------

-- ----------------------------
-- Table structure for servermanager_commands
-- ----------------------------
DROP TABLE IF EXISTS `servermanager_commands`;
CREATE TABLE `servermanager_commands`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `command` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `describe` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  `last_modify_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of servermanager_commands
-- ----------------------------

-- ----------------------------
-- Table structure for servermanager_emailsendlog
-- ----------------------------
DROP TABLE IF EXISTS `servermanager_emailsendlog`;
CREATE TABLE `servermanager_emailsendlog`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emailto` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `send_result` tinyint(1) NOT NULL,
  `creation_time` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of servermanager_emailsendlog
-- ----------------------------

SET FOREIGN_KEY_CHECKS = 1;
